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
    parser.add_argument("--index",
                        "-i",
                        type=int,
                        default=getenv('GMAE_CAPTURE_INDEX', 0),
                        help="OpenCV Index of the Video Capture Device"
                        )
    parser.add_argument("--fullscreen",
                        "-f",
                        type=bool,
                        default=env_means_true('GMAE_FULLSCREEN'),
                        help="Whether to start in full screen"
                        )
    parser.add_argument("--monitor",
                        "-m",
                        type=int,
                        default=getenv('GMAE_MONITOR', -1),
                        help="Which monitor number to launch the shit (default is the last one)"
                        )
    parser.add_argument("--audio-out",
                        "-audio",
                        type=str,
                        default=getenv('GMAE_AUDIO_OUTPUT', ''),
                        help="A (partial) string to identify the audio output, it will take the first that matches"
                        )
    parser.add_argument("--mute",
                        type=bool,
                        default=env_means_true('GMAE_MUTE'),
                        help="Whether to start in full screen"
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
    with AudioStream(args, name) as audio:
        log("Start Video Processor")
        with Processor(args, name, audio) as processor:
            processor.run()
