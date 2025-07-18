import subprocess
import os

from config import LOG_DIR, TARGET_URL

import tempfile

def run_vegeta_attack(rps, duration=60, target_url=TARGET_URL, log_prefix=""):
    attack_file = os.path.join(LOG_DIR, f"{log_prefix}_attack.bin")
    report_file = os.path.join(LOG_DIR, f"{log_prefix}_report.json")

    # Prepare a temp file with the target definition
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
        tmp.write(f"GET {target_url}\n")
        tmp.flush()
        tmp_target_file = tmp.name

    print(f"Running Vegeta attack: RPS={rps}, duration={duration}s")

    # Run vegeta attack and store binary output
    attack_cmd = f'vegeta attack -rate={rps} -duration={duration}s -format=json -targets={tmp_target_file} > "{attack_file}"'
    subprocess.run(attack_cmd, shell=True, check=True)

    # Generate JSON report
    report_cmd = f'vegeta report -type=json < "{attack_file}" > "{report_file}"'
    subprocess.run(report_cmd, shell=True, check=True)

    print(f"Saved logs: {attack_file}, {report_file}")

