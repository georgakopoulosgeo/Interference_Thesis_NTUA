import time
import threading
from collections import deque
import subprocess
import logging
from typing import List, Dict

logger = logging.getLogger("metrics-collector")

class MetricBuffer:
    def __init__(self, window_size: int = 30):
        self.buffer = deque(maxlen=window_size)
        self.lock = threading.Lock()
        self.last_sample_time = 0

    def add_sample(self, metrics: Dict):
        with self.lock:
            self.buffer.append({
                'timestamp': time.time(),
                'metrics': metrics
            })
            self.last_sample_time = time.time()

    def get_samples(self, window_seconds: int) -> List[Dict]:
        with self.lock:
            cutoff = time.time() - window_seconds
            return [sample for sample in self.buffer 
                   if sample['timestamp'] >= cutoff]

class PCMMetrics:
    @staticmethod
    def collect() -> Dict[str, float]:
        try:
            # Sample PCM command - adjust based on your actual PCM parameters
            result = subprocess.run(
                ["sudo", "pcm", "-csv", "-nc", "-silent", "-r", "1"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return PCMMetrics._parse_output(result.stdout)
        except Exception as e:
            logger.error(f"PCM collection failed: {str(e)}")
            return {}

    @staticmethod
    def _parse_output(csv_data: str) -> Dict[str, float]:
        """Parse PCM CSV output into your expected feature format"""
        # Example parsing - REPLACE WITH YOUR ACTUAL PCM OUTPUT PARSING
        lines = csv_data.strip().split('\n')
        headers = lines[0].split(',')
        values = lines[-1].split(',')
        
        return {
            'mean_cpu_util': float(values[headers.index('CPU_Util')]),
            'std_mem_bw': float(values[headers.index('Mem_BW')]),
            'p95_cache_miss': float(values[headers.index('L3_Miss')]),
            # Add all features your model expects
        }

class CollectorService:
    def __init__(self):
        self.buffer = MetricBuffer(window_size=30)
        self.running = False
        self.thread = None

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_collection, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def _run_collection(self):
        while self.running:
            metrics = PCMMetrics.collect()
            if metrics:  # Only store valid samples
                self.buffer.add_sample(metrics)
            time.sleep(1)  # Sampling interval

    def get_metrics(self, window_seconds: int = 20) -> Dict:
        samples = self.buffer.get_samples(window_seconds)
        if not samples:
            return {"error": "No metrics available"}
        
        # Aggregate samples (simple mean aggregation)
        aggregated = {}
        for key in samples[0]['metrics'].keys():
            values = [s['metrics'][key] for s in samples if key in s['metrics']]
            aggregated[f"mean_{key}"] = sum(values) / len(values)
            aggregated[f"std_{key}"] = (max(values) - min(values)) / 2  # Simplified std
        
        return {
            "window_seconds": window_seconds,
            "samples_count": len(samples),
            "metrics": aggregated,
            "timestamp": time.time()
        }