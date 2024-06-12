from dataclasses import dataclass
from datetime import datetime
from time import perf_counter
from typing import Optional

import cv2


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
    time: int
