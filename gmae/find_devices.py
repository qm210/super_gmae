from dataclasses import dataclass
from typing import Iterable

import cv2
from capture_devices import devices


@dataclass
class CaptureDeviceInfo:
    index: int
    width: int
    height: int
    fps: float
    frame_count: float
    info: Iterable[str]


def find_the_next_best_shit():
    captures = devices.run_with_param(device_type="video", result_=True)

    result = []
    for i, ingo in enumerate(captures):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            basic_info = CaptureDeviceInfo(
                i,
                int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                cap.get(cv2.CAP_PROP_FPS),
                cap.get(cv2.CAP_PROP_FRAME_COUNT),
                ingo
            )
            result.append(basic_info)
            cap.release()

    print("Found Capture Devices")
    for dev in result:
        print(dev)

    chosen = result[-1]
    print("For now, we will just take the last one:", chosen)
    return chosen
