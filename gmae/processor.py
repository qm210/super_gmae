import threading
from pathlib import Path
from time import perf_counter

import cv2
import glfw
import numpy as np
import pygame

from OpenGL.GL import *
from OpenGL.GL import shaders
from OpenGL.GLUT import *

from gmae.loop_state import LoopState, key_pressed
from gmae.utils import log, CaptureDeviceInfo, UniformLocations

WINDOW_HEIGHT = 1080

VERTEX_SHADER_FILE = "shaders/vertex.glsl"
FRAGMENT_SHADER_FILE = "shaders/frag.glsl"


class Processor:
    def __init__(self, device_index, device_name):
        self.capture = cv2.VideoCapture(device_index)
        self.capture_info = CaptureDeviceInfo.read_from(self.capture, name=device_name)
        if self.capture_info is None:
            raise RuntimeError("Video Device cannot be opened")
        else:
            print("Opened Device", device_index, self.capture_info)

        self.height = WINDOW_HEIGHT
        self.width = int(WINDOW_HEIGHT * self.capture_info.width / self.capture_info.height)

        pygame.init()
        self.overlay = pygame.display.set_mode(
            (self.width, self.height),
            pygame.DOUBLEBUF | pygame.OPENGL | pygame.HIDDEN
        )
        glfw.error_callback = self._glfw_error_callback

        self.window = self.init_window()
        glfw.make_context_current(self.window)

        folder = Path(__file__).resolve().parent
        self.vertex_shader_path = folder / VERTEX_SHADER_FILE
        self.fragment_shader_path = folder / FRAGMENT_SHADER_FILE

        # BL, BR, TR, TL
        self.vertices = np.array(
            [
                -1.0, +1.0, 0.0,
                +1.0, +1.0, 0.0,
                +1.0, -1.0, 0.0,
                -1.0, -1.0, 0.0,
            ],
            dtype=np.float32
        )
        # two triangles that give one square, as you can clearly see
        self.indices = np.array(
            [0, 1, 2, 0, 2, 3],
            dtype=np.uint,
        )

        self.is_compiling = False
        self.program, self.error = self.create_program()
        self.last_compiled_program = self.program
        self.last_compiler_error = self.error
        if self.error:
            print(self.error)
            raise RuntimeError("Could not compile shaders.")
        self.vao, self.vbo, self.ebo = self.create_objects()
        self.texture = glGenTextures(1)

        self.locations = UniformLocations(
            sampler=glGetUniformLocation(self.program, "iPixelData"),
            resolution=glGetUniformLocation(self.program, "iResolution"),
            time=glGetUniformLocation(self.program, "iTime"),
        )

        glClearColor(8.0, 0.0, 1.0, 1.0)  # some magenta shows that we didn't get far yet.
        glClear(GL_COLOR_BUFFER_BIT)
        self.raise_gl_error_if_exists()

        self.run_started_at = None
        self.first_run_completed = False
        log("Initialized Processor")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        glDeleteBuffers(1, [self.vbo])
        glDeleteBuffers(1, [self.ebo])
        glDeleteVertexArrays(1, [self.vao])
        glDeleteTextures(1, [self.texture])
        glfw.terminate()
        self.capture.release()

    def init_window(self):
        if not glfw.init():
            raise Exception("GLFW cannot initiailize.")
        window = glfw.create_window(
            self.width,
            self.height,
            "SUPER GMAE",
            None,
            None
        )
        if not window:
            glfw.terminate()
            raise Exception("GLFW cannot create window")
        return window

    def _glfw_error_callback(self, error, description):
        print("ERROR", error)
        # self.show_error(description)
        self.draw_text(description, self.width // 2, self.height // 2, (255, 0, 210))

    def show_error(self, message):
        # Convert the description to a Pygame Surface
        text_surface = pygame.font.Font(None, 24).render(message, True, (255, 0, 210))
        # Calculate the position to center the text
        text_rect = text_surface.get_rect(center=(400, 300))
        # Blit the text onto the screen
        self.overlay.blit(text_surface, text_rect)
        # Update the display
        pygame.display.flip()

    def draw_text(self, message, x=0, y=0, color=None):
        font = pygame.font.Font(None, 24)
        text_surface = font.render(message, True, color or (255, 255, 255))
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        width, height = text_surface.get_size()
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glRasterPos3d(x, y, 0)
        glDrawPixels(width, height, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
        glEnable(GL_DEPTH_TEST)
        glDisable(GL_BLEND)

    def create_program(self):
        self.is_compiling = True
        try:
            with open(self.vertex_shader_path, 'r') as file:
                vertex_shader_source = file.read()
        except Exception as exc:
            print("VERTEX SHADER FILE ERROR:", self.vertex_shader_path)
            raise exc
            # return None, "Vertex Shader File Error"
        try:
            vertex_shader = shaders.compileShader(vertex_shader_source, GL_VERTEX_SHADER)
        except shaders.ShaderCompilationError as exc:
            print("ERROR IN VERTEX SHADER ", exc.args[0])
            return None, exc.args[0]

        try:
            with open(self.fragment_shader_path, 'r') as file:
                fragment_shader_source = file.read()
        except Exception as exc:
            print("FRAGMENT SHADER FILE ERROR:", self.fragment_shader_path)
            raise exc
            # return None, "Fragment Shader File Error"
        try:
            fragment_shader = shaders.compileShader(fragment_shader_source, GL_FRAGMENT_SHADER)
        except shaders.ShaderCompilationError as exc:
            print("ERROR IN FRAGMENT SHADER", exc.args[0])
            return None, exc.args[0]

        try:
            program = shaders.compileProgram(vertex_shader, fragment_shader)
        except Exception as exc:
            print("ERROR IN COMPILE PROGRAM")
            return None, exc

        self.last_compiled_program = program
        self.is_compiling = False
        return program, None

    def create_objects(self):
        vao = glGenVertexArrays(1)
        vbo = glGenBuffers(1)
        ebo = glGenBuffers(1)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
        glBufferData(
            target=GL_ELEMENT_ARRAY_BUFFER,
            size=None,
            data=self.indices,
            usage=GL_STATIC_DRAW
        )

        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(
            target=GL_ARRAY_BUFFER,
            size=None,
            data=self.vertices,
            usage=GL_STATIC_DRAW
        )

        glBindVertexArray(vao)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(GLfloat), None)
        glEnableVertexAttribArray(0)

        # unbind again - unclear whether important
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

        return vao, vbo, ebo

    def load_texture(self, frame):
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_BORDER)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_BORDER)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGB,
            frame.shape[1],
            frame.shape[0],
            0,
            GL_BGR,
            GL_UNSIGNED_BYTE,
            frame.tobytes()
        )

    @staticmethod
    def raise_gl_error_if_exists():
        gl_error = glGetError()
        if gl_error:
            print("GL Error:", gl_error)
            raise RuntimeError("This sucks.")

    @staticmethod
    def execute_with_error_handling(label, func, *args):
        # OpenGL errors can be hard to trace, therefore this helper.
        try:
            func(*args)
            Processor.raise_gl_error_if_exists()
        except Exception as e:
            print(f"FAILED: {label}")
            raise e

    def setup_program(self):
        # framebuffer: int = glGenFramebuffers(1)
        # glBindFramebuffer(GL_FRAMEBUFFER, framebuffer)
        # glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.tex_id, 0)
        glUseProgram(self.program)
        glUniform1i(self.locations.sampler, 0)
        glUniform2f(self.locations.resolution, self.width, self.height)

        elapsed_seconds = (
            perf_counter() - self.run_started_at
            if self.run_started_at is not None
            else 0
        )
        glUniform1f(self.locations.time, elapsed_seconds)

    def render(self):
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, len(self.indices), GL_UNSIGNED_INT, self.indices)

    def process(self, frame):
        Processor.execute_with_error_handling(
            "LOAD TEXTURE",
            self.load_texture,
            frame,
        )
        Processor.execute_with_error_handling(
            "SETUP PROGRAM",
            self.setup_program,
        )
        Processor.execute_with_error_handling(
            "RENDER",
            self.render
        )
        Processor.execute_with_error_handling(
            "RENDER ERROR MESSAGE",
            self.draw_text,
            "LOL some tEXt",
        )
        Processor.execute_with_error_handling(
            "SWAP BUFFERS",
            glfw.swap_buffers,
            self.window
        )

    def trigger_shader_reload(self):
        self.compile_thread = threading.Thread(target=self.create_program)

    def run(self):
        if self.error:
            print("... Errors in Shaders, let's just give up.")
            return

        self.run_started_at = perf_counter()
        previous_state = LoopState.read(self)

        log("Now Run")
        while not glfw.window_should_close(self.window):
            ok, frame = self.capture.read()
            if not ok:
                break

            state_now = LoopState.read(self)
            if previous_state.f5_pressed and not state_now.f5_pressed:
                self.trigger_shader_reload()
            if previous_state.compiling and not state_now.compiling:
                self.program = self.last_compiled_program
            previous_state = state_now

            normalized_frame = self.normalize_frame(frame)
            self.process(frame)

            glfw.poll_events()

            if not self.first_run_completed:
                log("First processing completed.")
                self.first_run_completed = True

            if key_pressed(self.window, glfw.KEY_ESCAPE):
                break

    @staticmethod
    def normalize_frame(frame):
        in_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        normalized = cv2.normalize(in_rgb, None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        return normalized.astype(np.uint8)
