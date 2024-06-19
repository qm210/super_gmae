import argparse
from os import getenv
from platform import system

import cv2

from gmae.find_devices import find_capture_device_name_with_index
from gmae.processor import Processor
from gmae.utils import log


def parse_args():
    parser = argparse.ArgumentParser()

    index = getenv('GMAE_CV_INDEX', 0)
    parser.add_argument("--index",
                        type=int,
                        default=index,
                        help="OpenCV Index of the Video Capture Device"
                        )
    return parser.parse_args()


if __name__ == '__main__':
    print("CV2 version", cv2.__version__)
    if system().casefold() != "windows":
        raise OSError("Windows has won the game for now, sorry!")

    args = parse_args()

    log("Find Devices")
    name, index_ = find_capture_device_name_with_index()

    log("Start Processor")
    with Processor(args.index, name) as processor:
        processor.run()


# TODO
# HDMI-Audio ausgeben
# Fullscreen fixen
# Vergleich mit Kein-Shader auf Taste
# Überlegen wie man da coden kann
# NR4 loslegen lassen
