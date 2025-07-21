import time
import os
import json
from datetime import datetime, timezone
from typing import Optional, List
import random
import csv
import sys

from config import DURATION_MINUTES, STEP_INTERVAL, BASE_RPS, TARGET_URL, LOG_DIR, NGINX_METRICS_FIELDNAMES
from config import RPS_30MIN_GRADUAL_LOW, RPS_30MIN_GRADUAL_WIDE
from vegeta_runner import run_vegeta_attack
from parsing_and_storing import parse_vegeta_metrics, store_workload_metrics

TEST_ID = "FinalTest"

AVAILABLE_RPS_LISTS = {
    "RPS_30MIN_GRADUAL_LOW": RPS_30MIN_GRADUAL_LOW,
    "RPS_30MIN_GRADUAL_WIDE": RPS_30MIN_GRADUAL_WIDE
}


# Writes RPS to a JSONL file for Marla Controller
def log_rps_schedule_entry(minute, rps):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "minute": minute,
        "rps": rps
    }
    with open(os.path.join(LOG_DIR, "rps_schedule.jsonl"), "a") as f:
        f.write(json.dumps(entry) + "\n")


# Generates a per-minute RPS schedule based on a predefined list (we can aslo add random)
def generate_rps_schedule(duration_minutes: int = 30, predefined_rps: Optional[List[int]] = None) -> List[int]:
    if not predefined_rps:
        raise ValueError("You must provide a list of RPS levels for 'predefined' mode.")
    
    rps_values = []
    for rps_level in predefined_rps:
        rps_values.extend([rps_level] * 1)  # 1 minute per RPS level
    return (rps_values + [predefined_rps[-1]] * duration_minutes)[:duration_minutes]


# Main function to run the traffic test
def run_traffic_test(duration_minutes: int, predefined_rps: List[int], output_filename: str):
    print(f"Starting traffic test for {duration_minutes} minutes using list: {predefined_rps}")

    output_csv = f"{output_filename}.csv"
    os.makedirs(LOG_DIR, exist_ok=True)
    performance_csv = os.path.join(LOG_DIR, output_csv)

    with open(performance_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=NGINX_METRICS_FIELDNAMES)
        writer.writeheader()

    # Generate the RPS schedule
    rps_schedule = generate_rps_schedule(duration_minutes,predefined_rps)
    print(f"Generated RPS schedule: {rps_schedule}")


    # Loop over each minute - Every minute we run a vegeta attack with the given RPS and then store the metrics
    for minute, rps in enumerate(rps_schedule):
        print(f"[Minute {minute+1}] RPS = {rps}")
        
        # Log RPS for Marla's next cycle
        log_rps_schedule_entry(minute+1, rps)

        # Run vegeta attack
        report = run_vegeta_attack(rps=rps,duration=STEP_INTERVAL,target_url=TARGET_URL,log_prefix=f"minute_{minute+1}")

        # Parse metrics and store
        metrics = parse_vegeta_metrics(report)
        store_workload_metrics(csv_file=performance_csv,test_id=TEST_ID,minute=minute + 1,given_rps=rps,metrics=metrics)

        # Sleep exactly for the interval (if vegeta is async, else skip this)
        #time.sleep(STEP_INTERVAL)

    print("Traffic test completed.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 generator.py <rps_list_name> <output_csv_filename> [duration_minutes]")
        print(f"Available RPS lists: {', '.join(AVAILABLE_RPS_LISTS.keys())}")
        sys.exit(1)

    rps_list_name = sys.argv[1]
    output_filename = sys.argv[2]
    duration_minutes = int(sys.argv[3]) if len(sys.argv) > 3 else 30

    if rps_list_name not in AVAILABLE_RPS_LISTS:
        print(f"[ERROR] Invalid RPS list name: {rps_list_name}")
        print(f"Available options: {', '.join(AVAILABLE_RPS_LISTS.keys())}")
        sys.exit(1)

    rps_list = AVAILABLE_RPS_LISTS[rps_list_name]

    run_traffic_test(
        duration_minutes=duration_minutes,
        predefined_rps=rps_list,
        output_filename=output_filename
    )