from pathlib import Path
from time import perf_counter
from tkinter import Tk, messagebox

import cv2
import glfw
import numpy as np

from OpenGL.GL import *
from OpenGL.GL import shaders
from OpenGL.GLUT import *

from gmae.processor_utils import Rect, LoopState
from gmae.utils import log, CaptureDeviceInfo, UniformLocations, TitleInfo

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
        self.info = TitleInfo("SUPER GMAE")

        glfw.error_callback = self._glfw_error_callback

        self.window = self.init_window()
        self.fullscreen = False
        self.last_window_rect = None
        glfw.make_context_current(self.window)

        # we just use tkinter for error message boxes
        self.tk_root = Tk()
        self.tk_root.withdraw()

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

        self.program, self.error = self.compile_shaders()
        self.last_compiled_program = self.program
        self.last_compiler_error = self.error
        if self.error:
            self.show_error_popup(self.error, title="Cannot start with some compiling shaders.")
            return
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
        glfw.window_hint(glfw.RESIZABLE, glfw.FALSE)
        window = glfw.create_window(
            self.width,
            self.height,
            self.info.full_title,
            None,
            None
        )
        if not window:
            glfw.terminate()
            raise Exception("GLFW cannot create window")
        return window

    def _glfw_error_callback(self, error, description):
        print("ERROR", error)
        self.show_error_popup(description)
        # couldn't get text drawing to work for now. anyway.
        # self.draw_text(description, self.width // 2, self.height // 2, (255, 0, 210))

    @staticmethod
    def show_error_popup(message, title="Error"):
        messagebox.showerror(title, message)

    @staticmethod
    def print_error_prettier(exc, title=""):
        header, body_plus_end = exc.args[0].split(" b'")
        body, _ = body_plus_end.split("\\n'")
        error_lines = body.split("\\n")
        total_frame_length = 200
        upper_frame_length = total_frame_length - len("== ERROR IN ") - len(title) - 1
        print(f"== ERROR IN {title.upper()} =======" + upper_frame_length * "=")
        print(header)
        for line in error_lines:
            print(line)
        print(total_frame_length * "=")
        joined_errors = '\n'.join(error_lines)
        return f"{header}\n\n{joined_errors}"

    def compile_shaders(self):
        self.info.update(self.window, is_compiling=True)

        # could draw the file reading out of this because this could be done threaded (other than opengl). but not now
        try:
            with open(self.vertex_shader_path, 'r') as file:
                vertex_shader_source = file.read()
        except Exception as exc:
            print("VERTEX SHADER FILE ERROR:", self.vertex_shader_path)
            raise exc
        try:
            vertex_shader = shaders.compileShader(vertex_shader_source, GL_VERTEX_SHADER)
        except shaders.ShaderCompilationError as exc:
            message = self.print_error_prettier(exc, title="Vertex Shader")
            return None, message

        try:
            with open(self.fragment_shader_path, 'r') as file:
                fragment_shader_source = file.read()
        except Exception as exc:
            print("FRAGMENT SHADER FILE ERROR:", self.fragment_shader_path)
            raise exc
        try:
            fragment_shader = shaders.compileShader(fragment_shader_source, GL_FRAGMENT_SHADER)
        except shaders.ShaderCompilationError as exc:
            message = self.print_error_prettier(exc, title="Fragment Shader")
            return None, message

        try:
            program = shaders.compileProgram(vertex_shader, fragment_shader)
        except Exception as exc:
            print("ERROR IN COMPILE PROGRAM")
            return None, exc

        self.last_compiled_program = program
        self.info.update(self.window, is_compiling=False)
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

    def process(self, raw_frame):
        # frame = self.normalize_frame(raw_frame)
        frame = raw_frame
        Processor.execute_with_error_handling(
            "LOAD TEXTURE",
            self.load_texture,
            frame
        )
        Processor.execute_with_error_handling(
            "SETUP PROGRAM",
            self.setup_program,
        )
        Processor.execute_with_error_handling(
            "RENDER",
            self.render
        )
        glfw.swap_buffers(self.window)

    def run(self):
        if self.error:
            print("... Errors in Shaders, let's just give up.")
            return

        self.run_started_at = perf_counter()
        previously = LoopState()

        log("Now Run")
        while not glfw.window_should_close(self.window):
            ok, frame = self.capture.read()
            if not ok:
                break

            currently = LoopState.read(self)
            if previously.f5_pressed and not currently.f5_pressed:
                program, error = self.compile_shaders()
                if error:
                    self.show_error_popup(error, title="Cannot Replace Shaders")
                else:
                    log("Compiled Shaders (freshly from file).")
                    self.program = program
            if previously.f11_pressed and not currently.f11_pressed:
                self.toggle_fullscreen()
            previously = currently

            self.process(frame)
            if not self.first_run_completed:
                log("First processing completed.")
                self.first_run_completed = True

            glfw.poll_events()

            if self.key_pressed(glfw.KEY_ESCAPE):
                glfw.iconify_window(self.window)
            elif self.key_pressed(glfw.KEY_F4):
                break

    def key_pressed(self, key):
        return glfw.get_key(self.window, key) == glfw.PRESS

    def toggle_fullscreen(self):
        monitors = glfw.get_monitors()
        # get_window_monitor(self.window) breaks with some memory access error, I have no idea why
        # monitor = glfw.get_window_monitor(self.window)
        # monitor = glfw.get_primary_monitor()
        monitor = monitors[-1]
        print("For now, the full screen will always go to the last monitor available.")
        mode = glfw.get_video_mode(monitor)
        if self.fullscreen:
            x, y, self.width, self.height = self.last_window_rect.unpack()
            glfw.set_window_monitor(
                self.window, None, x, y, self.width, self.height, mode.refresh_rate
            )
        else:
            self.last_window_rect = Rect.read_window(self)
            aspect_ratio = self.height / self.width
            if mode.size.width > self.width:
                self.height = mode.size.height
                self.width = int(self.height / aspect_ratio)
            else:
                self.width = mode.size.width
                self.height = int(self.width * aspect_ratio)
            glfw.set_window_monitor(
                self.window, monitor, 0, 0, self.width, self.height, mode.refresh_rate
            )
        self.fullscreen = not self.fullscreen

    @staticmethod
    def normalize_frame(frame):
        in_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        normalized = cv2.normalize(in_rgb, None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        return normalized.astype(np.uint8)
