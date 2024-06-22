from enum import Enum
from math import exp
from pathlib import Path
from time import perf_counter
from tkinter import Tk, messagebox
from traceback import print_exception

import cv2
import glfw
import numpy as np

from OpenGL.GL import *
from OpenGL.GL import shaders
from OpenGL.GLUT import *

from gmae.processor_utils import Rect, LoopState, Key, EffectsState, EffectId
from gmae.utils import log, CaptureDeviceInfo, UniformLocations, TitleInfo

WINDOW_HEIGHT = 1080
SPACE_FOR_WINDOWS_SHIT = 80

VERTEX_SHADER_FILE = "shaders/original_vertex.glsl"
DRY_FRAGMENT_SHADER_FILE = "shaders/original_frag.glsl"
WET_FRAGMENT_SHADER_FILE = "shaders/frag.glsl"


class Processor:
    def __init__(self, args, device_name, audio_stream):
        device_index = args.index
        self.audio_stream = audio_stream
        self.capture = cv2.VideoCapture(device_index)
        self.capture_info = CaptureDeviceInfo.read_from(self.capture, name=device_name)
        if self.capture_info is None:
            raise RuntimeError("Video Device cannot be opened")
        else:
            print("Opened Device", device_index, self.capture_info)

        self.height = WINDOW_HEIGHT
        self.info = TitleInfo("SUPER GMAE")

        glfw.error_callback = self._glfw_error_callback

        self.window, self.monitor = self.init_window(args)
        self.last_window_rect = None
        glfw.make_context_current(self.window)
        self.fullscreen = False
        if args.fullscreen:
            self.toggle_fullscreen()

        # we just use tkinter for error message boxes
        self.tk_root = Tk()
        self.tk_root.withdraw()

        folder = Path(__file__).resolve().parent
        self.vertex_shader_path = folder / VERTEX_SHADER_FILE
        self.dry_fragment_shader_path = folder / DRY_FRAGMENT_SHADER_FILE
        self.wet_fragment_shader_path = folder / WET_FRAGMENT_SHADER_FILE

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

        self.vertex_shader = None
        self.dry_fragment_shader = None
        self.wet_fragment_shader = None
        self.dry_program = None
        self.use_dry_program = False
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
            effect_amount={
                EffectId.A: glGetUniformLocation(self.program, "aEffectA"),
                EffectId.B: glGetUniformLocation(self.program, "aEffectB"),
                EffectId.C: glGetUniformLocation(self.program, "aEffectC"),
                EffectId.D: glGetUniformLocation(self.program, "aEffectD"),
                EffectId.GreenBlob: glGetUniformLocation(self.program, "aEffectGreenBlob"),
            }
        )
        self.dry_locations = UniformLocations(
            sampler=glGetUniformLocation(self.dry_program, "iPixelData"),
            resolution=glGetUniformLocation(self.dry_program, "iResolution"),
        )

        glClearColor(8.0, 0.0, 1.0, 1.0)  # some magenta shows that we didn't get far yet.
        glClear(GL_COLOR_BUFFER_BIT)
        self.raise_gl_error_if_exists()

        self.effects = EffectsState.random()
        self.elapsed_seconds = 0
        self.last_step_at = None
        self.run_started_at = None
        self.first_run_completed = False
        log("Initialized Processor")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.program is not None:
            glDeleteBuffers(1, [self.vbo])
            glDeleteBuffers(1, [self.ebo])
            glDeleteVertexArrays(1, [self.vao])
            glDeleteTextures(1, [self.texture])
        glfw.destroy_window(self.window)
        glfw.terminate()
        self.capture.release()

    @property
    def width(self):
        """
        As this assumes landscape orientation, the height is what counts and the width is derived
        """
        return int(self.height * self.capture_info.width / self.capture_info.height)

    def init_window(self, args):
        if not glfw.init():
            raise Exception("GLFW cannot initiailize.")
        monitors = glfw.get_monitors()
        try:
            monitor = monitors[args.monitor]
        except Exception as exc:
            print_exception(exc)
            monitor = None
        mode = glfw.get_video_mode(monitor)
        print("Monitor Mode:", str(mode))
        self.height = min(self.height, mode.size.height - SPACE_FOR_WINDOWS_SHIT)
        glfw.window_hint(glfw.RESIZABLE, glfw.FALSE)
        glfw.window_hint(glfw.FOCUS_ON_SHOW, glfw.TRUE)
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
        x, y = glfw.get_monitor_pos(monitor)
        x += (mode.size.width - self.width) // 2
        y += (mode.size.height - self.height) // 2
        glfw.set_window_monitor(
            window,
            None,
            x,
            y,
            self.width,
            self.height,
            mode.refresh_rate
        )
        return window, monitor

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

        # do not refresh vertex and original fragment shader later, these are fixed

        if self.vertex_shader is None:
            # could draw the file reading to a different thread. not important right now.
            try:
                with open(self.vertex_shader_path, 'r') as file:
                    vertex_shader_source = file.read()
            except Exception as exc:
                print("VERTEX SHADER FILE ERROR:", self.vertex_shader_path)
                raise exc
            try:
                self.vertex_shader = shaders.compileShader(vertex_shader_source, GL_VERTEX_SHADER)
            except shaders.ShaderCompilationError as exc:
                message = self.print_error_prettier(exc, title="Vertex Shader")
                return None, message

        if self.dry_fragment_shader is None:
            try:
                with open(self.dry_fragment_shader_path, 'r') as file:
                    original_fragment_shader_source = file.read()
            except Exception as exc:
                print("DRY FRAGMENT SHADER FILE ERROR:", self.dry_fragment_shader_path)
                raise exc
            try:
                self.dry_fragment_shader = shaders.compileShader(original_fragment_shader_source, GL_FRAGMENT_SHADER)
            except shaders.ShaderCompilationError as exc:
                message = self.print_error_prettier(exc, title="Dry Fragment Shader")
                return None, message

        if self.dry_program is None:
            try:
                self.dry_program = shaders.compileProgram(self.vertex_shader, self.dry_fragment_shader)
            except Exception as exc:
                print("ERROR IN COMPILE DRY PROGRAM")
                return None, exc

        try:
            with open(self.wet_fragment_shader_path, 'r') as file:
                fragment_shader_source = file.read()
        except Exception as exc:
            print("FRAGMENT SHADER FILE ERROR:", self.wet_fragment_shader_path)
            raise exc
        try:
            self.wet_fragment_shader = shaders.compileShader(fragment_shader_source, GL_FRAGMENT_SHADER)
        except shaders.ShaderCompilationError as exc:
            message = self.print_error_prettier(exc, title="Fragment Shader")
            return None, message

        try:
            program = shaders.compileProgram(self.vertex_shader, self.wet_fragment_shader)
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
        glUseProgram(
            self.program
            if not self.use_dry_program
            else self.dry_program
        )
        locations = (
            self.locations
            if not self.use_dry_program
            else self.dry_locations
        )
        glUniform1i(locations.sampler, 0)
        glUniform2f(locations.resolution, self.width, self.height)

        if self.last_step_at is None:
            self.last_step_at = self.run_started_at
        current_step_at = perf_counter()
        delta_seconds = current_step_at - self.last_step_at
        self.elapsed_seconds += delta_seconds
        self.last_step_at = current_step_at

        if locations.time is not None:
            glUniform1f(locations.time, self.elapsed_seconds)

        for effect_id in EffectId:
            flash = self.effects.next_flash.get(effect_id, None)
            if flash is None:
                self.effects.choose_next_flash(effect_id=effect_id)
                continue
            amount_location = locations.effect_amount.get(effect_id, -1)
            if amount_location < 0:
                continue

            flash.remaining_sec -= delta_seconds
            strength = self.effects.strength.get(effect_id, 0)
            amount = strength * flash.current_value
            glUniform1f(amount_location, amount)
            if flash.is_over:
                self.effects.choose_next_flash(effect_id=effect_id)

    def render(self):
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, len(self.indices), GL_UNSIGNED_INT, self.indices)

    def process(self, frame):
        # frame = self.normalize_frame(frame)
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
        self.elapsed_seconds = 0
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
            if previously.f8_pressed and not currently.f8_pressed:
                self.use_dry_program = not self.use_dry_program
            if previously.f11_pressed and not currently.f11_pressed:
                self.toggle_fullscreen()
            if previously.f12_pressed and not currently.f12_pressed:
                self.audio_stream.toggle_mute()
            previously = currently

            self.effects.handle_input(self)

            self.process(frame)

            if not self.first_run_completed:
                log("First processing completed.")
                self.first_run_completed = True

            if self.key_pressed(glfw.KEY_ESCAPE):
                if self.fullscreen:
                    break
                else:
                    glfw.iconify_window(self.window)
            if self.key_pressed(Key.ABORT):
                break
            if self.key_pressed(Key.PRINT_DEBUG):
                print("======= DEBUG =======")
                print("Running Time:", self.elapsed_seconds, "sec")
                self.effects.print_debug()
                self.audio_stream.print_debug()

            glfw.poll_events()

    def key_pressed(self, key):
        if isinstance(key, Enum):
            key = key.value
        return glfw.get_key(self.window, key) == glfw.PRESS

    def toggle_fullscreen(self):
        # get_window_monitor(self.window) breaks with some memory access error, I have no idea why
        # monitor = glfw.get_window_monitor(self.window)
        # monitor = glfw.get_primary_monitor()
        # ah well. let's pass it by CLI argument.
        mode = glfw.get_video_mode(self.monitor)
        if self.fullscreen:
            x, y, _w, self.height = self.last_window_rect.unpack()
            glfw.set_window_monitor(
                self.window, None, x, y, self.width, self.height, mode.refresh_rate
            )
        else:
            self.last_window_rect = Rect.read_window(self)
            aspect_ratio = self.height / self.width
            self.height = (
                mode.size.height
                if mode.size.width >= self.width
                else int(mode.size.width * aspect_ratio)
            )
            glfw.set_window_monitor(
                self.window, self.monitor, 0, 0, self.width, self.height, mode.refresh_rate
            )
        self.fullscreen = not self.fullscreen
        print("Is now fullscreen?", self.fullscreen, "(full screen will always be on the last monitor available.")

    @staticmethod
    def normalize_frame(frame):
        in_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        normalized = cv2.normalize(in_rgb, None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        return normalized.astype(np.uint8)
