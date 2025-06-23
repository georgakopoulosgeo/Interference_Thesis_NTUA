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
        self.domain_filter = "core"
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
                header_domain = next(reader)  # First header (domains)
                header_metric = next(reader)  # Second header (metrics)
                
                # Process all rows (not just the first one)
                for row in reader:
                    if not row:
                        continue  # Skip empty rows

                    # Extract timestamp (assuming "Date" and "Time" columns exist)
                    timestamp = None
                    row_metrics = {}
                    
                    for idx, (dom, met) in enumerate(zip(header_domain, header_metric)):
                        dom_l = dom.strip().lower()
                        met_l = met.strip().lower()
                        
                        # Always capture "Date" and "Time" for timestamps
                        if met_l in ("date", "time"):
                            # row_metrics[met_l] = row[idx]
                            if met_l == "date":
                                date_str = row[idx]
                            elif met_l == "time":
                                time_str = row[idx]
                            continue
                        
                        # Filter other metrics
                        if (self.domain_filter in dom_l) and any(kw in met_l for kw in self.desired_keywords):
                            name = f"{dom.strip()}_{met.strip()}"
                            try:
                                row_metrics[name] = float(row[idx])
                            except ValueError:
                                pass
                    
                    # We use that?
                    # Combine date/time into a timestamp (if available)
                    if "date_str" in locals() and "time_str" in locals():
                        timestamp_str = f"{date_str} {time_str}"
                        try:
                            timestamp = time.mktime(time.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S"))
                        except ValueError:
                            timestamp = time.time()  # Fallback to current time
                    
                    if row_metrics:  # Only add non-empty metrics
                        metrics_series.append({
                            "timestamp": timestamp,
                            "System - Date": date_str,
                            "System - Time": time_str,
                            **row_metrics
                        })

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