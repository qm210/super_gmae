from platform import system

import cv2

from gmae.find_devices import find_the_next_best_shit
from gmae.processor import Processor


if __name__ == '__main__':
    print("CV2 version", cv2.__version__)
    if system().casefold() != "windows":
        raise OSError("Windows has won the game for now, sorry!")

    device_info = find_the_next_best_shit()
    with Processor(device_info) as processor:
        processor.run()
