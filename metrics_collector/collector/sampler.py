import time
import threading
from .pcm_reader import PCMReader
from .buffer import RollingBuffer

class Sampler(threading.Thread):
    """
    Background thread that periodically reads PCM metrics and stores them.
    """
    def __init__(self, collection_duration_sec: float = 20.0, sampling_interval_sec: float = 60.0, buffer_window_sec: float = 60.0):
        super().__init__(daemon=True)
        self.collection_duration = collection_duration_sec  # How long to run PCM each time
        self.sampling_interval = sampling_interval_sec    # How often to collect (60s)
        self.reader = PCMReader()
        self.buffer = RollingBuffer(buffer_window_sec)
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.is_set():
            ts = time.time()
            metrics = self.reader.read_metrics(self.collection_duration)
            self.buffer.add(ts, metrics)
            
            # Sleep for remaining interval time
            elapsed = time.time() - ts
            sleep_time = max(0, self.sampling_interval - elapsed)
            time.sleep(sleep_time)

    def stop(self):
        self._stop_event.set()