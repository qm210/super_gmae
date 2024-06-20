import argparse
from os import getenv
from platform import system

import cv2

from gmae.find_video_captures import find_capture_device_name_with_index
from gmae.AudioStream import AudioStream
from gmae.processor import Processor
from gmae.utils import log, env_means_true


def parse_args():
    parser = argparse.ArgumentParser()

    capture_index = getenv('GMAE_CAPTURE_INDEX', 0)
    parser.add_argument("--index",
                        "-i",
                        type=int,
                        default=capture_index,
                        help="OpenCV Index of the Video Capture Device"
                        )
    fullscreen = env_means_true('GMAE_FULLSCREEN')
    parser.add_argument("--fullscreen",
                        "-f",
                        type=bool,
                        default=fullscreen,
                        help="Whether to start in full screen"
                        )
    monitor_index = getenv('GMAE_MONITOR', -1)
    parser.add_argument("--monitor",
                        "-m",
                        type=int,
                        default=monitor_index,
                        help="Which monitor number to launch the shit (default is the last one)"
                        )
    return parser.parse_args()


if __name__ == '__main__':
    print("CV2 version", cv2.__version__)
    if system() != "Windows":
        raise OSError("Windows has won the game for now, sorry!")

    args = parse_args()

    log("Find Devices")
    name, index_ = find_capture_device_name_with_index()

    log("Start Audio Stream")
    with AudioStream(name, mute=True) as audio:
        log("Start Video Processor")
        with Processor(args, name, audio) as processor:
            processor.run()
