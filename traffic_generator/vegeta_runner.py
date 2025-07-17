import subprocess
import os

from config import LOG_DIR

def run_vegeta_attack(rps, duration=60, target_url="http://nginx.default.svc.cluster.local", log_prefix=""):
    """
    Executes a Vegeta load test at the specified RPS for `duration` seconds.
    Saves output in both binary and JSON format for analysis.
    """
    attack_file = os.path.join(LOG_DIR, f"{log_prefix}_attack.bin")
    report_file = os.path.join(LOG_DIR, f"{log_prefix}_report.json")
    target_definition = f"GET {target_url}"

    print(f"Running Vegeta attack: RPS={rps}, duration={duration}s")

    # Run vegeta attack and store binary output
    attack_cmd = (
        f'echo "{target_definition}" | '
        f'vegeta attack -rate={rps} -duration={duration}s -format=json > "{attack_file}"'
    )
    subprocess.run(attack_cmd, shell=True, check=True)

    # Generate JSON report
    report_cmd = f'vegeta report -type=json < "{attack_file}" > "{report_file}"'
    subprocess.run(report_cmd, shell=True, check=True)

    print(f"Saved logs: {attack_file}, {report_file}")
