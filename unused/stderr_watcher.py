from io import StringIO


class StderrWatcher:
    def __init__(self):
        self.string_io = StringIO()
        self.stream = self.string_io

    def write(self, line):
        self.string_io.write(line)
        if "[ERROR:0" in line:
            print("Haha", line)

    def flush(self):
        pass
