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
            cmd = [self.pcm_path, "2", f"-csv={tmp_path}"]
            
            # Remove timeout or increase it significantly
            subprocess.run(
                cmd,
                timeout=duration + 5,  # Give extra 5s buffer
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            metrics = {}
            with open(tmp_path, newline="") as csvfile:
                reader = csv.reader(csvfile)
                header_domain = next(reader)
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
            return metrics

        except subprocess.TimeoutExpired:
            print("⚠️ PCM timed out - returning empty metrics")
            return {}  # Avoid crashing, return empty data

        except Exception as e:
            print(f"⚠️ PCM Error: {e}")
            return {}

        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
