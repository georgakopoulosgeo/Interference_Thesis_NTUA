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
    Invokes Intel PCM and parses hardware counters, filtering only
    the 'system' domain metrics with our desired keywords.
    """
    def _parse_core_range(self, core_str: str) -> List[int]:
        """Convert "0-2" into [0,1,2] with validation"""
        if not core_str:
            raise ValueError("ASSIGNED_CORES environment variable is empty")
        
        try:
            if '-' in core_str:
                start, end = map(int, core_str.split('-'))
                return list(range(start, end+1))
            return [int(core_str)]
        except ValueError as e:
            raise ValueError(f"Invalid core range format: {core_str}") from e

    def __init__(self, pcm_path: str = "/usr/local/bin/pcm"):
        self.pcm_path = pcm_path
        self.domain_filter = "system"
        self.desired_keywords = [
            "ipc", "l2miss", "l3miss", "read", "write",
            "c0res%", "c1res%", "c6res%"
        ]
        # Only parse cores if in core-filtering mode
        if self.domain_filter == "core":
            core_str = os.getenv("ASSIGNED_CORES")
            if not core_str:
                raise RuntimeError("ASSIGNED_CORES environment variable not set")
            self.assigned_cores = self._parse_core_range(core_str)
        else:
            self.assigned_cores = []  # Not used in system mode
        self.node_name = os.getenv("NODE_NAME", "unknown-node")

    
    def _filter_core_metrics(self, raw_metrics: dict) -> dict:
        """Keep only metrics for our assigned cores"""
        filtered = {}
        core_pattern = re.compile(r'core_(\d+)')
        
        for metric, value in raw_metrics.items():
            match = core_pattern.search(metric)
            if match:
                core_num = int(match.group(1))
                if core_num in self.assigned_cores:
                    filtered[metric] = value
            else:
                # Keep non-core-specific metrics
                filtered[metric] = value
        
        # Add node identification
        filtered["node_name"] = self.node_name
        filtered["assigned_cores"] = ','.join(map(str, self.assigned_cores))
        return filtered

    def read_metrics(self, duration) -> list[dict]:
        """Returns a list of metric dictionaries (one per timestamp)."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            cmd = [self.pcm_path, "2", "-csv=" + tmp_path]
            try:
                subprocess.run(cmd, timeout=duration, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.TimeoutExpired:
                print("PCM monitoring completed: duration reached.", file=sys.stderr)

            # Read raw CSV data
            with open(tmp_path, 'r') as f:
                raw_csv = f.read()
                print(f"Raw CSV (first 100 chars):\n{raw_csv[:100]}...", file=sys.stderr)  # Debug

            metrics_series = []
            print(f"Assigned cores: {self.assigned_cores}", file=sys.stderr)
            with open(tmp_path, newline="") as csvfile:
                reader = csv.reader(csvfile)
                header_domain = next(reader)  # First header (domains)
                header_metric = next(reader)  # Second header (metrics)
                
                # Prepare lists of indices to keep.
                indices_to_keep = []
                for idx, (dom, met) in enumerate(zip(header_domain, header_metric)):
                    met_lower = met.strip().lower()
                    dom_lower = dom.strip().lower()
                    # Always include if the metric is "date" or "time"
                    if met_lower in ("date", "time"):
                        indices_to_keep.append(idx)
                    if self.domain_filter == "core":
                        if "core" in dom_lower:
                            tokens = dom_lower.replace("(", "").split()
                            try:
                                core_token = next(t for t in tokens if t.startswith("core"))
                                core_id_str = core_token.replace("core", "")
                                core_id = int(core_id_str)
                                if core_id in self.assigned_cores:
                                    if any(kw in met_lower for kw in self.desired_keywords):
                                        indices_to_keep.append(idx)
                            except (StopIteration, ValueError, IndexError):
                                continue  # skip bad labels
                    elif self.domain_filter == "system":
                        is_system = "system" in dom_lower
                        is_core_0_to_5 = "core" in dom_lower and any(f"core{n}" in dom_lower for n in range(6))
                        if (is_system or is_core_0_to_5) and any(kw in met_lower for kw in self.desired_keywords):
                            indices_to_keep.append(idx)
                if not indices_to_keep:
                    print("⚠️ No matching metrics found for specified cores and keywords.", file=sys.stderr)
                    return []
                else:
                    print(f"Keeping {len(indices_to_keep)} metrics, indices: {indices_to_keep}", file=sys.stderr)
                        
                for row in reader:
                    if not row:
                        continue

                    if len(row) <= max(indices_to_keep):
                        print(f"⚠️ Skipping row with only {len(row)} columns, expected at least {max(indices_to_keep)+1}", file=sys.stderr)
                        continue
                    filtered_row = [row[i] for i in indices_to_keep]
                    row_dict = {}
                    date_str, time_str = None, None
                    timestamp = None

                    for i, idx in enumerate(indices_to_keep):
                        domain = header_domain[idx].strip()
                        metric = header_metric[idx].strip()
                        key = f"{domain}_{metric}"
                        value = filtered_row[i].strip()
                        key_lower = metric.lower()

                        if key_lower == "date":
                            date_str = value
                        elif key_lower == "time":
                            time_str = value
                        else:
                            try:
                                row_dict[key] = float(value)
                            except ValueError:
                                pass  # Ignore non-numeric values

                    if date_str and time_str:
                        try:
                            timestamp = time.mktime(time.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S"))
                        except ValueError:
                            timestamp = time.time()
                    else:
                        timestamp = time.time()

                    final_dict = {
                        "System - Date": date_str,
                        "System - Time": time_str,
                        "timestamp": timestamp,
                        **row_dict,  # includes the actual metrics
                        "node_name": self.node_name,
                        "assigned_cores": ",".join(map(str, self.assigned_cores))
                    }
                    metrics_series.append(final_dict)


            print(f"Collected {len(metrics_series)} metric samples.", file=sys.stderr)
            return metrics_series

        except Exception as e:
            print(f"⚠️ PCM Error: {e}", file=sys.stderr)
            return []  # Return empty list on failure

        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass