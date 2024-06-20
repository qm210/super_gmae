import argparse
from os import getenv
from platform import system

import cv2
import sounddevice as sd

from gmae.find_devices import find_capture_device_name_with_index, find_corresponding_sound_devices, \
    get_sound_stream_parameters
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

    sound_input, sound_output = find_corresponding_sound_devices(name)
    stream_params = get_sound_stream_parameters(sound_input, sound_output)

    log("Start Audio Stream")
    with sd.Stream(**stream_params):
        log("Start Video Processor")
        with Processor(args, name) as processor:
            processor.run()


# TODO
# HDMI-Audio ausgeben
# Überlegen wie updates eingespielt werden. man da coden kann
