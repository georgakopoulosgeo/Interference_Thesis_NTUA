#!/usr/bin/env python3
"""
NGINX Interference Test Coordinator
- Runs multiple interference scenarios
- Tests with varying replicas (1-5) and RPS (100 to max_RPS)
- Integrates PCM monitoring
- Saves results to CSV files
"""

import os
import time
import csv
import threading
import subprocess
from typing import List, Dict, Optional

# Import monitoring functions
from system_monitor_intepcm import pcm_monitoring

# Configuration
NGINX_SERVICE_URL = "http://192.168.49.2:30080"
WRK_PATH = "/home/george/Workspace/Interference/workloads/wrk2/wrk"
MAX_RPS = 500  # Adjust based on your earlier findings
DURATION = "40s"  # Test duration per run
THREADS = 1
CONCURRENT_CONNS = 200
SLEEP_BETWEEN_TESTS = 40

# Test matrix
REPLICAS_TO_TEST = range(1, 3)  # 1-5 replicas
RPS_STEPS = range(100, MAX_RPS + 1, 200)  # 100, 300, ..., MAX_RPS

# Directory setup
RAW_LOG_FOLDER = "raw_logs"
BASELINE_RESULTS_DIR = "results"
os.makedirs(RAW_LOG_FOLDER, exist_ok=True)
os.makedirs(BASELINE_RESULTS_DIR, exist_ok=True)

# Interference scenarios
INTERFERENCE_SCENARIOS = [
    {"id": 1, "name": "Baseline", "type": None},
    {"id": 2, "name": "1 iBench CPU pod", "type": "ibench-cpu", "count": 1},
    {"id": 3, "name": "2 iBench CPU pods", "type": "ibench-cpu", "count": 2},
    {"id": 6, "name": "1 stress-ng l3 pod", "type": "stress-ng-l3", "count": 1},
    {"id": 7, "name": "2 stress-ng l3 pods", "type": "stress-ng-l3", "count": 2},
    {"id": 10, "name": "1 iBench memBW pod", "type": "ibench-membw", "count": 1}
]

def create_interference(scenario: Dict) -> bool:
    """Placeholder for interference creation function"""
    print(f"Would create interference: {scenario['name']}")
    return True  # For now, just pretend we succeeded

def run_workload(rps: int) -> Dict:
    """Placeholder for workload execution function"""
    print(f"Would run workload at {rps} RPS")
    # Return dummy metrics for now
    return {
        "Throughput": rps * 0.9,
        "Avg_Latency": 50,
        "P50_Latency": 45,
        "P75_Latency": 60,
        "P90_Latency": 80,
        "P99_Latency": 120,
        "Max_Latency": 150
    }

def test_coordinator():
    """Main test execution loop with proper synchronization"""
    test_case_id = int(time.time())
    
    # Initialize results file
    results_file = os.path.join(BASELINE_RESULTS_DIR, "workload_metrics.csv")
    with open(results_file, "w") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "Timestamp", "TestID", "Replicas", "Interference", "InterferenceID", 
            "Given_RPS", "Throughput", "Avg_Latency", "P50_Latency", 
            "P75_Latency", "P90_Latency", "P99_Latency", "Max_Latency"
        ])
        writer.writeheader()

    for replicas in REPLICAS_TO_TEST:
        # Scale NGINX once per replica count
        print(f"\n=== Scaling NGINX to {replicas} replicas ===")
        subprocess.run(["kubectl", "scale", "deployment", "my-nginx", f"--replicas={replicas}"], check=True)
        time.sleep(10)  # Wait for scaling to complete

        for rps in RPS_STEPS:
            for scenario in INTERFERENCE_SCENARIOS:
                print(f"\n[Replicas={replicas}|RPS={rps}] Testing {scenario['name']}")

                # Setup interference
                if scenario["type"] and not create_interference(scenario):
                    print(f"Skipping failed scenario {scenario['name']}")
                    continue
                time.sleep(4)  # Stabilization period

                # Generate unique test ID
                test_id = f"{test_case_id}_{scenario['id']}_{replicas}_{rps}"
                print(f"Starting test {test_id}")

                # Set up monitoring files
                pcm_raw_file = os.path.join(RAW_LOG_FOLDER, f"pcm_raw_{test_id}.csv")
                pcm_system_file = os.path.join(BASELINE_RESULTS_DIR, f"pcm_system_{test_id}.csv")
                pcm_core_file = os.path.join(BASELINE_RESULTS_DIR, f"pcm_core_{test_id}.csv")

                # Start PCM monitoring in a separate thread
                monitoring_duration = 45  # Slightly longer than test duration
                pcm_thread = threading.Thread(
                    target=pcm_monitoring,
                    args=(monitoring_duration, 1000, pcm_raw_file, pcm_system_file, pcm_core_file)
                )
                pcm_thread.start()
                time.sleep(2)  # Give PCM time to start

                # Run workload
                print(f"Starting workload at {rps} RPS")
                start_time = time.time()
                metrics = run_workload(rps)
                elapsed_time = time.time() - start_time
                print(f"Workload completed in {elapsed_time:.2f} seconds")

                # Wait for monitoring to complete
                pcm_thread.join()

                # Save results
                result_row = {
                    "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "TestID": test_id,
                    "Replicas": replicas,
                    "Interference": scenario["name"],
                    "InterferenceID": scenario["id"],
                    "Given_RPS": rps,
                    **metrics
                }

                with open(results_file, "a") as f:
                    writer = csv.DictWriter(f, fieldnames=[
                        "Timestamp", "TestID", "Replicas", "Interference", "InterferenceID", 
                        "Given_RPS", "Throughput", "Avg_Latency", "P50_Latency", 
                        "P75_Latency", "P90_Latency", "P99_Latency", "Max_Latency"
                    ])
                    writer.writerow(result_row)

                # Clean up interference if needed
                if scenario["type"]:
                    print(f"Cleaning up interference: {scenario['name']}")
                    # Placeholder for cleanup logic

                time.sleep(SLEEP_BETWEEN_TESTS)  # Cool-down period

if __name__ == "__main__":
    test_coordinator()