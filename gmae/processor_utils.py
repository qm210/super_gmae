from enum import Enum
from math import exp
from random import random, uniform
from typing import TYPE_CHECKING

import glfw

from dataclasses import dataclass, field

from gmae.utils import clamp

if TYPE_CHECKING:
    from gmae.processor import Processor


class Key(Enum):
    ABORT = glfw.KEY_F4
    UPDATE_SHADER = glfw.KEY_F5
    FULLSCREEN = glfw.KEY_F11
    MUTE = glfw.KEY_F12
    SHOW_ORIGINAL = glfw.KEY_F8
    PRINT_DEBUG = glfw.KEY_F1

    # effect annoyance controls
    INCREASE_GREEN_BLOB = glfw.KEY_Q
    DECREASE_GREEN_BLOB = glfw.KEY_A
    INCREASE_EFFECT_A = glfw.KEY_W
    DECREASE_EFFECT_A = glfw.KEY_S
    INCREASE_EFFECT_B = glfw.KEY_E
    DECREASE_EFFECT_B = glfw.KEY_D
    INCREASE_EFFECT_C = glfw.KEY_R
    DECREASE_EFFECT_C = glfw.KEY_F
    INCREASE_EFFECT_D = glfw.KEY_T
    DECREASE_EFFECT_D = glfw.KEY_G
    RANDOMIZE_ALL_EFFECTS = glfw.KEY_X


@dataclass
class LoopState:
    f5_pressed: bool = False
    f8_pressed: bool = False
    f11_pressed: bool = False
    f12_pressed: bool = False
    compiling: bool = False

    @classmethod
    def read(cls, processor: "Processor"):
        return cls(
            f5_pressed=processor.key_pressed(Key.UPDATE_SHADER),
            f8_pressed=processor.key_pressed(Key.SHOW_ORIGINAL),
            f11_pressed=processor.key_pressed(Key.FULLSCREEN),
            f12_pressed=processor.key_pressed(Key.MUTE),
            compiling=processor.info.is_compiling,
        )


class EffectId(Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    GreenBlob = "GreenBlob"


effect_keymap = {
    Key.INCREASE_EFFECT_A: (EffectId.A, +1),
    Key.DECREASE_EFFECT_A: (EffectId.A, -1),
    Key.INCREASE_EFFECT_B: (EffectId.B, +1),
    Key.DECREASE_EFFECT_B: (EffectId.B, -1),
    Key.INCREASE_EFFECT_C: (EffectId.C, +1),
    Key.DECREASE_EFFECT_C: (EffectId.C, -1),
    Key.INCREASE_EFFECT_D: (EffectId.D, +1),
    Key.DECREASE_EFFECT_D: (EffectId.D, -1),
    Key.INCREASE_GREEN_BLOB: (EffectId.GreenBlob, +1),
    Key.DECREASE_GREEN_BLOB: (EffectId.GreenBlob, -1),
}


@dataclass
class EffectFlash:
    remaining_sec: float
    duration_sec: float

    _min_seconds_between_flashes = 20
    _max_seconds_between_flashes = 90
    _min_seconds_flash_duration = 3
    _max_seconds_flash_duration = 50

    def __init__(self):
        super().__init__()
        self.remaining_sec = uniform(
            EffectFlash._min_seconds_between_flashes,
            EffectFlash._max_seconds_between_flashes
        )
        self.duration_sec = uniform(
            EffectFlash._min_seconds_flash_duration,
            EffectFlash._max_seconds_flash_duration
        )

    @property
    def current_value(self):
        if 0 >= self.remaining_sec >= -self.duration_sec:
            return 0
        x = -self.remaining_sec / (2 * self.duration_sec)
        return exp(-x * x)

    @property
    def is_over(self):
        return self.remaining_sec < -self.duration_sec


@dataclass
class EffectsState:
    strength: dict = field(default_factory=dict)
    next_flash: dict = field(default_factory=dict)

    @classmethod
    def random(cls):
        amount = {effect_id: 0 for effect_id in EffectId}
        result = cls(strength=amount)
        result.randomize_amounts()
        return result

    def randomize_amounts(self):
        for effect_id in self.strength:
            self.strength[effect_id] = random()

    def print_debug(self):
        print("Effect Strengths now:")
        for id in self.strength:
            print(f"  {id.name} = {self.strength[id]}")

    def handle_input(self, processor: "Processor"):
        if processor.key_pressed(Key.RANDOMIZE_ALL_EFFECTS):
            self.randomize_amounts()
            return

        for key in Key:
            params = effect_keymap.get(key)
            if params is None:
                continue
            if processor.key_pressed(key):
                id, inc = params
                self.change(id, inc)

    def change(self, id: EffectId, inc):
        step_size = 0.1
        if id not in self.strength:
            self.strength[id] = 1
        else:
            self.strength[id] = clamp(
                self.strength[id] + inc * step_size
            )
        print(f"Amount of Effect {id} now:", self.strength[id])

    def choose_next_flash(self, effect_id=None):
        if effect_id is None:
            for id in EffectId:
                self.choose_next_flash(effect_id=id)
            return
        self.next_flash[effect_id] = EffectFlash()


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
