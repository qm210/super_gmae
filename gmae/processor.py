from ctypes import c_float

import cv2
import glfw
import numpy as np

from OpenGL.GL import *
from OpenGL.GL import shaders
from OpenGL.GLUT import *
from OpenGL.arrays import vbo as vbo_arrays

from gmae.shaders.basic import vertex_shader_source, fragment_shader_source


class Processor:
    def __init__(self, device):
        self.width = device.width
        self.height = device.height
        self.window = self._init_window()
        glfw.make_context_current(self.window)

        self.capture = cv2.VideoCapture(device.index)

        # BL, BR, TR, TL
        self.vertices = np.array(
            [
                -1.0, -1.0, 0.0,
                +1.0, -1.0, 0.0,
                +1.0, +1.0, 0.0,
                -1.0, +1.0, 0.0
            ],
            dtype=np.float32
        )
        # two triangles that give one square, as you can clearly see
        self.indices = np.array(
            [0, 1, 2, 0, 2, 3],
            dtype=np.uint,
        )

        self.program, self.error = self._create_program()
        self.vao, self.vbo, self.ebo = self._create_objects()
        self.tex_id = glGenTextures(1)
        self.sampler_location = glGetUniformLocation(self.program, "textureSampler")
        self.resolution_location = glGetUniformLocation(self.program, "iResolution")

        self.raise_gl_error_if_exists()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        glDeleteBuffers(1, [self.vbo])
        glDeleteBuffers(1, [self.ebo])
        glDeleteVertexArrays(1, [self.vao])
        glDeleteTextures(1, [self.tex_id])
        glfw.terminate()
        self.capture.release()

    def _init_window(self):
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

    @staticmethod
    def _create_program():
        try:
            vertex_shader = shaders.compileShader(vertex_shader_source, GL_VERTEX_SHADER)
        except shaders.ShaderCompilationError as exc:
            print("ERROR IN VERTEX SHADER", exc.args[0])
            return None, exc.args[0]
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
        return program, None

    def _create_objects(self):
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
        glBindTexture(GL_TEXTURE_2D, self.tex_id)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
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

    def process(self, frame):
        try:
            self.load_texture(frame)
            self.raise_gl_error_if_exists()
        except Exception as e:
            print("LOAD TEXTURE FAILED")
            raise e

        glClearColor(1.0, 0.3, 0.3, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)

        try:
            glUseProgram(self.program)
            self.raise_gl_error_if_exists()
        except Exception as e:
            print("USE PROGRAM FAILED")
            raise e

        try:
            glUniform1i(self.sampler_location, self.tex_id)
            glUniform2f(self.resolution_location, self.width, self.height)
            self.raise_gl_error_if_exists()
        except Exception as e:
            print("SETTING UNIFORMS FAILED")
            raise e

        try:
            glBindVertexArray(self.vao)
            self.raise_gl_error_if_exists()
            glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, self.indices)
            self.raise_gl_error_if_exists()
        except Exception as e:
            print("DRAWING FAILED")
            raise e

        try:
            glfw.swap_buffers(self.window)
            glfw.poll_events()
        except Exception as e:
            print("SWAP BUFFERS / POLL EVENTS FAILED")
            raise e

    def run(self):
        if self.error:
            print("... Errors in Shaders, let's just give up.")
            return

        while not glfw.window_should_close(self.window):
            ret, frame = self.capture.read()
            if not ret:
                break
            # normalized_frame = self.normalize_frame(frame)
            self.process(frame)

    @staticmethod
    def normalize_frame(frame):
        in_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        normalized = cv2.normalize(in_rgb, None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        return normalized.astype(np.uint8)
