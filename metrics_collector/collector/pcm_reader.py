import datetime
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
            with open(tmp_path, newline="") as csvfile:
                reader = csv.reader(csvfile)
                header_domain = next(reader)   # e.g. ["System","Socket","Core",…]
                header_metric = next(reader)   # e.g. ["Date","Time","IPC","L2MISS",…]

                for row in reader:
                    if not row:
                        continue  # skip empty lines

                    # Reset per‐row
                    date_str = None
                    time_str = None
                    row_metrics = {}

                    # Extract date/time columns and filter numeric ones
                    for idx, dom in enumerate(header_domain):
                        met = header_metric[idx] if idx < len(header_metric) else ""
                        dom_l = dom.strip().lower()
                        met_l = met.strip().lower()
                        cell = row[idx].strip()

                        # Always capture date/time
                        if met_l == "date":
                            date_str = cell
                            continue
                        if met_l == "time":
                            time_str = cell
                            continue

                        # Otherwise only keep if domain & keyword match
                        if self.domain_filter.strip().lower() in dom_l and any(kw in met_l for kw in [kw.lower() for kw in self.desired_keywords]):
                            try:
                                row_metrics[f"{dom.strip()}_{met.strip()}"] = float(cell)
                            except ValueError:
                                pass  # skip non-numeric

                    # Build timestamp
                    if date_str:
                        fmt = "%Y-%m-%d %H:%M:%S" if time_str else "%Y-%m-%d"
                        dt_str = f"{date_str} {time_str}" if time_str else date_str
                        try:
                            dt = datetime.datetime.strptime(dt_str, fmt)
                        except ValueError:
                            dt = datetime.datetime.now()
                        timestamp = dt.timestamp()
                    else:
                        timestamp = time.time()

                    # Assemble the record
                    entry = {
                        "timestamp": timestamp,
                        "date": date_str,
                        "time": time_str,
                        **row_metrics
                    }
                    metrics_series.append(entry)

            return metrics_series

        except Exception as e:
            print(f"⚠️ PCM Error: {e}", file=sys.stderr)
            return []  # Return empty list on failure

        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass