import subprocess
import csv
import tempfile
import os
import sys
import time

class PCMReader:
    """
    Invokes Intel PCM and parses hardware counters, filtering only
    the 'system' domain metrics with our desired keywords.
    """
    def __init__(self, pcm_path: str = "/usr/local/bin/pcm"):
        self.pcm_path = pcm_path
        self.domain_filter = "system"
        self.desired_keywords = [
            "ipc", "l2miss", "l3miss", "read", "write",
            "c0res%", "c1res%", "c6res%"
        ]

    def read_metrics(self, duration) -> list[dict]:
        """Returns metrics with PCM's native timestamps (System-Data + System-Time)."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            cmd = [self.pcm_path, "2", "-csv=" + tmp_path]
            try:
                subprocess.run(cmd, timeout=duration, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.TimeoutExpired:
                print("PCM monitoring completed: duration reached.", file=sys.stderr)

            metrics_series = []
            with open(tmp_path, newline="") as csvfile:
                reader = csv.reader(csvfile)
                header_domain = next(reader)  # e.g., ["System", "System", ...]
                header_metric = next(reader)  # e.g., ["Data", "Time", "IPC", ...]
                
                for row in reader:
                    if not row:
                        continue

                    # Extract System-Data and System-Time
                    row_metrics = {}
                    
                    for idx, (dom, met) in enumerate(zip(header_domain, header_metric)):
                        dom_l = dom.strip().lower()
                        met_l = met.strip().lower()

                        # Combine Date + Time columns
                        if met_l == "data" and dom_l == "system":
                            date_str = row[idx]
                        elif met_l == "time" and dom_l == "system":
                            time_str = row[idx]
                        # Filter other metrics
                        elif (self.domain_filter in dom_l) and any(kw in met_l for kw in self.desired_keywords):
                            name = f"{dom.strip()}_{met.strip()}"
                            try:
                                row_metrics[name] = float(row[idx])
                            except ValueError:
                                pass

                    # Only add entries with valid metrics
                    if row_metrics and "date_str" in locals() and "time_str" in locals():
                        metrics_series.append({
                            "System-Data": date_str,
                            "System-Time": time_str,
                            **row_metrics
                        })

            return metrics_series

        except Exception as e:
            print(f"PCM Error: {e}", file=sys.stderr)
            return []
        finally:
            os.unlink(tmp_path)