import time
import threading
from collections import deque

class RollingBuffer:
    """
    Keeps a time-stamped rolling window of metric samples.
    """
    def __init__(self, window_size_sec: float):
        self.window_size = window_size_sec
        self.buffer = deque()  # stores tuples of (timestamp, metrics_dict)
        self.lock = threading.Lock()

    def add(self, timestamp: float, metrics: dict):
        with self.lock:
            self.buffer.append((timestamp, metrics))
            # Purge stale entries
            while self.buffer and (timestamp - self.buffer[0][0]) > self.window_size:
                self.buffer.popleft()

    def snapshot(self, window_sec: float) -> list:
        """
        Returns all metric dicts in the last `window_sec` seconds.
        """
        cutoff = time.time() - window_sec
        with self.lock:
            return [m for ts, m in self.buffer if ts >= cutoff]