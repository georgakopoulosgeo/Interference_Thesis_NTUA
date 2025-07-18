import subprocess
import os
import json
from typing import Any, Dict
import tempfile

from config import LOG_DIR, TARGET_URL

def run_vegeta_attack(rps: int, duration: int = 60, target_url: str = TARGET_URL, log_prefix: str = "") -> Dict[str, Any]:
    """
    Executes a Vegeta load test at the specified RPS for `duration` seconds.
    Saves output in both binary and JSON format for analysis.
    """
    attack_file = os.path.join(LOG_DIR, f"{log_prefix}_attack.bin")
    report_file = os.path.join(LOG_DIR, f"{log_prefix}_report.json")

    # Prepare targets file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_target_file:
        tmp_target_file.write(f"GET {target_url}\n")
        tmp_target_file.flush()
        targets_path = tmp_target_file.name

    print(f"Running Vegeta attack: RPS={rps}, duration={duration}s")

    try:
        # Run vegeta attack
        subprocess.run([
            "vegeta", "attack",
            "-rate", str(rps),
            "-duration", f"{duration}s",
            "-format", "json",
            "-targets", targets_path,
            "-output", attack_file
        ], check=True)

        # Run vegeta report
        with open(report_file, "w") as f:
            subprocess.run([
                "vegeta", "report",
                "-type=json",
                attack_file
            ], stdout=f, check=True)

        print(f"Saved logs: {attack_file}, {report_file}")

        # Optionally return report data
        with open(report_file) as f:
            return json.load(f)

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Vegeta failed: {e}")
        return {}

    finally:
        # Clean up temp targets file
        if os.path.exists(targets_path):
            os.remove(targets_path)
