from math import sin

import sounddevice as sd


class AudioStream:
    def __init__(self, name, mute=False):
        input_device, output_device = self.find_corresponding_sound_devices(name)
        self.params = self.get_sound_stream_parameters(input_device, output_device)
        self.stream = sd.Stream(**self.params)
        self.mute = mute
        self.stream.start()
        self.first_timestamp = None

    def __enter__(self):
        return self

    def __exit__(self, _type, _val, _tb):
        self.stream.stop()

    @staticmethod
    def find_corresponding_sound_devices(name):
        all_devices = sd.query_devices()
        input_device = next((
            device
            for device in all_devices
            if device['max_input_channels'] > 0
            and name in device['name']
        ), None)
        output_devices = [
            device
            for device in all_devices
            if device['max_output_channels'] > 0
        ]
        default_output_index = sd.default.device[0]
        output_device = output_devices[default_output_index]
        return input_device, output_device

    def get_sound_stream_parameters(self, input, output):
        # sd.default is always a (Output, Input) Tuple, it seems
        output_dtype = sd.default.dtype[0]

        # the stream callback will receive an optimal (and possibly varying)
        # number of frames based on host requirements and the requested latency settings
        blocksize = 0

        return {
            'device': (input['index'], output['index']),
            'channels': output['max_output_channels'],
            'samplerate': output['default_samplerate'],
            'blocksize': blocksize,
            'dtype': output_dtype,
            'callback': self.play_thru
        }

    def play_thru(self, indata, outdata, _frames, time, _status):
        if self.first_timestamp is None:
            self.first_timestamp = time.currentTime
        # don't need for now. anyway.
        # elapsed_sec = time.currentTime - self.first_timestamp
        gain = 0 if self.mute else 1
        outdata[:] = gain * indata

    def toggle_mute(self):
        self.mute = not self.mute
