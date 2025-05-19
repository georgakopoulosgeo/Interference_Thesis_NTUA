import time
import threading
from .pcm_reader import PCMReader
from .buffer import RollingBuffer

class Sampler(threading.Thread):
    """
    Background thread that periodically reads PCM metrics and stores them.
    """
    def __init__(self, interval_sec: float = 1.0, buffer_window_sec: float = 30.0):
        super().__init__(daemon=True)
        self.interval = interval_sec
        self.reader = PCMReader()
        self.buffer = RollingBuffer(buffer_window_sec)
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.is_set():
            ts = time.time()
            metrics = self.reader.read_metrics(self.interval)
            self.buffer.add(ts, metrics)
            time.sleep(self.interval)

    def stop(self):
        self._stop_event.set()
