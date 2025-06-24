import subprocess
import csv
import tempfile
import os
import re
import sys
import time
from typing import List

class PCMReader:
    """
    Reads core-specific Intel PCM metrics for assigned cores only.
    """
    def _parse_core_range(self, core_str: str) -> List[int]:
        """Convert core range string like '0-2' into [0, 1, 2]"""
        if not core_str:
            raise ValueError("ASSIGNED_CORES environment variable is empty")

        if '-' in core_str:
            start, end = map(int, core_str.split('-'))
            return list(range(start, end + 1))
        return [int(core_str)]

    def __init__(self, pcm_path: str = "/usr/local/bin/pcm"):
        self.pcm_path = pcm_path
        self.assigned_cores = self._parse_core_range(os.getenv("ASSIGNED_CORES", ""))
        self.node_name = os.getenv("NODE_NAME", "unknown-node")
        self.keep_metrics = ['IPC', 'L3MISS', 'L2MISS', 'C0res%', 'C1res%', 'C6res%']

    def read_metrics(self, duration: int) -> list[dict]:
        """Runs PCM and returns list of filtered metric dicts for each timestamp."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            cmd = [self.pcm_path, "2", "-csv=" + tmp_path]
            try:
                subprocess.run(cmd, timeout=duration, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.TimeoutExpired:
                print("PCM monitoring completed (timeout reached)", file=sys.stderr)

            # Load and parse CSV
            with open(tmp_path, newline="") as csvfile:
                reader = csv.reader(csvfile)
                header_domain = next(reader)
                header_metric = next(reader)

                columns = list(zip(header_domain, header_metric))
                metrics_series = []

                for row in reader:
                    if not row:
                        continue
                    
                    timestamp, date_str, time_str = None, None, None
                    row_metrics = {}

                    for idx, (domain, metric) in enumerate(columns):
                        domain = domain.strip()
                        metric = metric.strip()

                        if metric.lower() == "date":
                            date_str = row[idx]
                            continue
                        elif metric.lower() == "time":
                            time_str = row[idx]
                            continue

                        # Match only if it's a core metric for our assigned cores
                        core_match = re.match(r"Core(\d+)", domain)
                        if core_match:
                            core_id = int(core_match.group(1))
                            if core_id in self.assigned_cores and metric in self.keep_metrics:
                                key = f"core_{core_id}_{metric}"
                                try:
                                    row_metrics[key] = float(row[idx])
                                except ValueError:
                                    pass  # skip non-numeric values

                    if date_str and time_str:
                        try:
                            timestamp = time.mktime(time.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S"))
                        except ValueError:
                            timestamp = time.time()

                    if row_metrics:
                        row_metrics.update({
                            "timestamp": timestamp,
                            "System - Date": date_str,
                            "System - Time": time_str,
                            "node_name": self.node_name,
                            "assigned_cores": ",".join(map(str, self.assigned_cores)),
                        })
                        metrics_series.append(row_metrics)

                print(f"Collected {len(metrics_series)} filtered samples.", file=sys.stderr)
                return metrics_series

        except Exception as e:
            print(f"⚠️ PCM Error: {e}", file=sys.stderr)
            return []

        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
