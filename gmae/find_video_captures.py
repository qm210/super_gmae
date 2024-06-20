import cv2
from capture_devices import devices
import sounddevice as sd

from gmae.utils import log


HDMI_USB_ADAPTER_SEARCH_STRING = "ugreen"


def take_preferred_index(names):
    if len(names) == 1:
        return 0

    def name_find(search_str, exclude=False):
        search_casefold = search_str.casefold()
        return next((
            name
            for name in names
            if (not exclude and search_casefold in name.casefold())
            or (exclude and search_casefold not in name.casefold())
        ), None)

    name_with_search_string = name_find(HDMI_USB_ADAPTER_SEARCH_STRING)
    if name_with_search_string is not None:
        return names.index(name_with_search_string)
    non_integrated = name_find("integrated", exclude=True)
    if non_integrated is not None:
        return names.index(non_integrated)
    return names[-1]


def find_capture_device_name_with_index():
    device_names = devices.run_with_param(device_type="video", result_=True)
    log("Scanned Video Capture Devices.")
    for name in device_names:
        print("-> ", name)
    if not device_names:
        raise EnvironmentError("There are no Video Capture devices.")

    # THIS DOES NOT WORK - the orders of the device_names and the open CV indices are different. lel
    index = take_preferred_index(device_names)

    actual_name = device_names[index].split(':')[-1].strip()
    return actual_name, index
