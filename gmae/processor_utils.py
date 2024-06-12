from typing import TYPE_CHECKING

import glfw

from dataclasses import dataclass

if TYPE_CHECKING:
    from gmae.processor import Processor


@dataclass
class LoopState:
    f5_pressed: bool = False
    f11_pressed: bool = False
    compiling: bool = False

    @classmethod
    def read(cls, processor: "Processor"):
        return cls(
            f5_pressed=processor.key_pressed(glfw.KEY_F5),
            f11_pressed=processor.key_pressed(glfw.KEY_F11),
            compiling=processor.info.is_compiling,
        )


@dataclass
class Rect:
    x: int
    y: int
    width: int
    height: int

    def unpack(self):
        return self.x, self.y, self.width, self.height

    @classmethod
    def read_window(cls, processor: "Processor"):
        x, y = glfw.get_window_pos(processor.window)
        return cls(x, y, processor.width, processor.height)
