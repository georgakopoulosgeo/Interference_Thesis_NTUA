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
    
            # Open & parse headers + decide which columns to keep
            with open(tmp_path, newline="") as csvfile:
                reader = csv.reader(csvfile)
                header_domain = next(reader)
                header_metric = next(reader)
                
                indices_to_keep = []
                for idx, (dom, met) in enumerate(zip(header_domain, header_metric)):
                    dom_l = dom.strip().lower()
                    met_l = met.strip().lower()
                    if met_l in ("date", "time"):
                        indices_to_keep.append(idx)
                    elif (self.domain_filter.lower() in dom_l
                        and any(kw.lower() in met_l for kw in self.desired_keywords)):
                        indices_to_keep.append(idx)
                
                if not indices_to_keep:
                    print(f"No columns matched for domain filter '{self.domain_filter}' "
                        f"with keywords {self.desired_keywords}.", file=sys.stderr)
                    return []  # or raise an exception
                
                # Build the combined‐header row
                combined_header = [
                    f"{header_domain[i]} - {header_metric[i]}"
                    for i in indices_to_keep
                ]
                metrics_series.append(combined_header)
                
                # Process each data row
                for row in reader:
                    if not row:
                        continue
                    # Simply pick out the columns we're keeping
                    filtered_row = [row[i] for i in indices_to_keep]
                    metrics_series.append(filtered_row)
            
            print(f"Collected {len(metrics_series)-1} metric samples "
                f"(plus 1 header row).", file=sys.stderr)
            return metrics_series

        except Exception as e:
            print(f"⚠️ PCM Error: {e}", file=sys.stderr)
            return []  # Return empty list on failure

        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass