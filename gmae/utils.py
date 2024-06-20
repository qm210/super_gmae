from dataclasses import dataclass
from datetime import datetime
from os import getenv
from time import perf_counter
from typing import Optional

import cv2
import glfw


def timestamp():
    return datetime.now().isoformat()


last_counter = None


def log(*args):
    global last_counter
    counter = perf_counter()
    diff = ""
    if last_counter is not None:
        delta = counter - last_counter
        diff = f"({delta:.4f}s)"
    print(f"{timestamp()} {diff}|", *args)
    last_counter = counter


@dataclass
class CaptureDeviceInfo:
    width: int
    height: int
    fps: float
    frame_count: float
    name: str = ""

    @classmethod
    def read_from(cls, capture, name="") -> Optional["CaptureDeviceInfo"]:
        if not capture.isOpened():
            return None
        return cls(
            int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            capture.get(cv2.CAP_PROP_FPS),
            capture.get(cv2.CAP_PROP_FRAME_COUNT),
            name=name,
        )


@dataclass
class UniformLocations:
    sampler: int
    resolution: int
    time: Optional[int] = None


@dataclass
class TitleInfo:
    name: str
    is_compiling: bool = False

    @property
    def full_title(self):
        result = self.name
        if self.is_compiling:
            result += " (Compiling...)"
        return result

    def update(self, window, name=None, is_compiling=None):
        if name is not None:
            self.name = name
        if is_compiling is not None:
            self.is_compiling = is_compiling
        glfw.set_window_title(window, self.full_title)


def env_means_true(name: str):
    return getenv(name, "").casefold() in ["true", "1", "on"]
