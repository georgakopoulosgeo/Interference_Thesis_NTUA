import time
import os
import json
from datetime import datetime, timezone
from typing import Optional, List
import random
import csv

from config import DURATION_MINUTES, STEP_INTERVAL, BASE_RPS, TARGET_URL, LOG_DIR, NGINX_METRICS_FIELDNAMES
from config import RPS_30MIN_GRADUAL_LOW, RPS_30MIN_GRADUAL_WIDE
from vegeta_runner import run_vegeta_attack
from parsing_and_storing import parse_vegeta_metrics, store_workload_metrics

NAME_OF_PERFORMANCE_METRICS_FILE = "perfomance_naive.csv"
TEST_ID = "naive_1"


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
def generate_rps_schedule(duration_minutes: int = 30, base_rps: int = 1500, mode: str = "predefined", predefined_rps: Optional[List[int]] = None) -> List[int]:
    if mode == "predefined":
        if not predefined_rps:
            raise ValueError("You must provide a list of RPS levels for 'predefined' mode.")
        
        rps_values = []
        for rps_level in predefined_rps:
            rps_values.extend([rps_level] * 1)  # 1 minute per RPS level
        return (rps_values + [predefined_rps[-1]] * duration_minutes)[:duration_minutes]
    else:
        raise ValueError("Only 'predefined' mode is supported in this version.")


# Main function to run the traffic test
def run_traffic_test(duration_minutes: int = DURATION_MINUTES,mode: str = "predefined",base_rps: int = BASE_RPS,predefined_rps: Optional[List[int]] = None):
    
    print(f"Starting traffic test for {duration_minutes} minutes")
    test_id = TEST_ID
    
    # Create logs directory if needed
    os.makedirs(LOG_DIR, exist_ok=True)
    performance_csv = os.path.join(LOG_DIR, "performance_metrics.csv")

    # Explicitly write headers once
    with open(performance_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=NGINX_METRICS_FIELDNAMES)
        writer.writeheader()

    # Generate the RPS schedule
    rps_schedule = generate_rps_schedule(duration_minutes=duration_minutes,base_rps=base_rps,mode=mode,predefined_rps=predefined_rps)
    print(f"Generated RPS schedule: {rps_schedule}")


    # Loop over each minute - Every minute we run a vegeta attack with the given RPS and then store the metrics
    for minute, rps in enumerate(rps_schedule):
        print(f"[Minute {minute+1}] RPS = {rps}")
        
        # Log RPS for MARLA
        log_rps_schedule_entry(minute+1, rps)

        # Run vegeta attack
        report = run_vegeta_attack(rps=rps,duration=STEP_INTERVAL,target_url=TARGET_URL,log_prefix=f"minute_{minute+1}")

        # Parse metrics and store
        metrics = parse_vegeta_metrics(report)
        store_workload_metrics(csv_file=performance_csv,test_id=test_id,minute=minute + 1,given_rps=rps,metrics=metrics)

        # Sleep exactly for the interval (if vegeta is async, else skip this)
        #time.sleep(STEP_INTERVAL)

    print("Traffic test completed.")


if __name__ == "__main__":
    run_traffic_test(
        duration_minutes=DURATION_MINUTES,
        mode="predefined",
        base_rps=BASE_RPS,
        predefined_rps=RPS_30MIN_GRADUAL_WIDE
    )