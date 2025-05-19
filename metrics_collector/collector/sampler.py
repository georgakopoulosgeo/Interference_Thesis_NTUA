import time
import threading
from .pcm_reader import PCMReader
from .buffer import RollingBuffer
import sys

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
            print(f"⏱️ Collecting metrics (duration={self.collection_duration}s)...", file=sys.stderr)  # DEBUG
            metrics_list = self.reader.read_metrics(self.collection_duration)
            time.sleep(self.sampling_interval)  # Sleep for the sampling interval

            print(f"📊 Metrics collected: {len(metrics_list)} samples.", file=sys.stderr)

            for metrics in metrics_list:
                self.buffer.add(metrics.get("timestamp", ts), metrics)
            #self.buffer.add(ts, metrics)

    def stop(self):
        self._stop_event.set()