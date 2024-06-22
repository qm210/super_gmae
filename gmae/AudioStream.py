import sounddevice as sd


class AudioStream:
    def __init__(self, args, name, mute=False):
        self.input_device, self.output_device = \
            self.find_corresponding_sound_devices(name, args.audio_out)
        self.stream = self.create_stream()
        self.mute = mute
        if self.stream is not None:
            self.stream.start()
        # for debugging
        self.first_timestamp = None
        self.max_amplitude_since_unmuting = 0

    def __enter__(self):
        return self

    def __exit__(self, _type, _val, _tb):
        if self.stream is None:
            return
        self.stream.stop()

    def create_stream(self):
        if self.input_device is None or self.output_device is None:
            print("You need to have both Audio Input and Output for the Stream to work!")
            return None
        params = self.get_sound_stream_parameters(
            self.input_device,
            self.output_device,
            self.play_thru
        )
        print("Audio Stream Parameters:")
        for key, value in params.items():
            if key != "callback":
                print(f"  {key}: {value}")
        return sd.Stream(**params)

    @staticmethod
    def find_corresponding_sound_devices(input_name, output_name=""):
        all_devices = sd.query_devices()
        print("DEBUG - All Audio Devices")
        for device in all_devices:
            function = ""
            if device['max_input_channels'] > 0:
                function += "I"
            if device['max_output_channels'] > 0:
                function += "O"
            if function == "":
                function = "--"
            function += ":"
            if len(function) == 2:
                function += " "
            name = device['name'].replace('\r', '').replace('\n', '')
            print(f"  {function} {name} - {device['index']} - {device['hostapi']}")

        input_device = next((
            device
            for device in all_devices
            if device['max_input_channels'] > 0
            and input_name in device['name']
        ), None)
        output_devices = [
            device
            for device in all_devices
            if device['max_output_channels'] > 0
        ]
        output_device = None
        if output_name:
            output_device = next((
                device
                for device in output_devices
                if output_name in device['name']
            ), None)
        if output_device is None:
            default_output_index = sd.default.device[0]
            output_device = output_devices[default_output_index]

        return input_device, output_device

    @staticmethod
    def get_sound_stream_parameters(input, output, callback):
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
            'callback': callback
        }

    def play_thru(self, indata, outdata, _frames, time, _status):
        if self.first_timestamp is None:
            self.first_timestamp = time.currentTime
        # don't need for now. anyway.
        # elapsed_sec = time.currentTime - self.first_timestamp
        gain = 0 if self.mute else 1
        outdata[:] = gain * indata
        self.max_amplitude_since_unmuting = abs(indata.max())

    def toggle_mute(self):
        self.mute = not self.mute
        if not self.mute:
            self.max_amplitude_since_unmuting = 0

    def print_debug(self):
        print("Audio Input Device", self.input_device)
        print("Audio Output Device", self.output_device)
        muted_info = " [MUTED]" if self.mute else ""
        print("Max Amplitude:", self.max_amplitude_since_unmuting, muted_info)
