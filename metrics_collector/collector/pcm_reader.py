import subprocess
import csv
import tempfile
import os

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

    def read_metrics(self, duration) -> dict:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            cmd = [self.pcm_path, "1", "-csv=" + tmp_path]
            subprocess.run(cmd, timeout=duration + 5, check=True)  # Ensure command succeeds

            # DEBUG: Log the raw CSV content
            with open(tmp_path, 'r') as f:
                raw_csv = f.read()
                print(f"Raw CSV content: {raw_csv}")  # DEBUG: Verify PCM output

            metrics = {}
            with open(tmp_path, newline="") as csvfile:
                reader = csv.reader(csvfile)
                header_domain = next(reader)  # Skip headers
                header_metric = next(reader)
                row = next(reader, None)
                
                if row:
                    for idx, (dom, met) in enumerate(zip(header_domain, header_metric)):
                        dom_l = dom.strip().lower()
                        met_l = met.strip().lower()
                        if self.domain_filter in dom_l and any(kw in met_l for kw in self.desired_keywords):
                            name = f"{dom.strip()}_{met.strip()}"
                            try:
                                metrics[name] = float(row[idx])
                            except ValueError:
                                pass
            
            print(f"Extracted metrics: {metrics}")  # DEBUG: Verify parsed data
            return metrics

        except Exception as e:
            print(f"⚠️ PCM Error: {e}")
            return {}  # Return empty dict on failure

        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass