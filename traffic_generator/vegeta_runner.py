import subprocess
import os
import json
from typing import Dict, Any

from config import LOG_DIR, TARGET_URL

def run_vegeta_attack(rps: int, duration: int = 60, target_url: str = TARGET_URL, log_prefix: str = "") -> Dict[str, Any]:
    """Execute Vegeta attack and return parsed performance report."""

    # Define output paths
    targets_path = os.path.join(LOG_DIR, f"{log_prefix}_targets.txt")
    results_path = os.path.join(LOG_DIR, f"{log_prefix}_attack.bin")
    report_path = os.path.join(LOG_DIR, f"{log_prefix}_report.json")

    try:
        # Write target definition
        with open(targets_path, "w") as f:
            f.write(f"GET {target_url}\n")  # newline is essential

        # Run vegeta attack
        subprocess.run([
            "vegeta", "attack",
            "-rate", str(rps),
            "-duration", f"{duration}s",
            "-format", "json",
            "-targets", targets_path,
            "-output", results_path
        ], check=True)

        # Run vegeta report
        with open(report_path, "w") as f:
            subprocess.run([
                "vegeta", "report",
                "-type=json",
                results_path
            ], stdout=f, check=True)

        # Load and return report
        with open(report_path) as f:
            return json.load(f)

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Vegeta test failed: {e}", flush=True)
        return {}

    finally:
        # Optional cleanup — comment this out if you want to keep logs
        for path in [targets_path, results_path, report_path]:
            if os.path.exists(path):
                os.remove(path)
