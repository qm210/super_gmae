from typing import TYPE_CHECKING

import glfw

from dataclasses import dataclass

if TYPE_CHECKING:
    from gmae.processor import Processor


def key_pressed(window, key):
    return glfw.get_key(window, key) == glfw.PRESS


@dataclass
class LoopState:
    f5_pressed: bool = False
    compiling: bool = False

    @classmethod
    def read(cls, processor: "Processor"):
        return cls(
            f5_pressed=key_pressed(processor.window, glfw.KEY_F5),
            compiling=processor.info.is_compiling,
        )
