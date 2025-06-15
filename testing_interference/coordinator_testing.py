#!/usr/bin/env python3
import os
import csv
import datetime
import argparse
import subprocess
import time
from typing import List, Dict, Optional
from system_monitor_intepcm import pcm_monitoring
from workload_run_monitor import run_workload_single_pod, parse_workload_output_single_pod, store_workload_metrics, parse_workload_output
import threading

# Global configuration
NGINX_SERVICE_URL = "http://192.168.49.2:30080"
WRK_PATH = "/home/george/Workspace/Interference/workloads/wrk2/wrk"
NGINX_SCRIPT = "/home/george/Workspace/Interference/workloads/nginx/run_nginx.py"
MAX_RPS = 300  # Adjust based on your earlier findings
DURATION = "40s"  # Test duration per run
THREADS = 1
CONCURRENT_CONNS = 200
SLEEP_BETWEEN_TESTS = 40

# Test matrix
REPLICAS_TO_TEST = range(1, 3)  # 1-5 replicas
RPS_STEPS = range(100, MAX_RPS + 1, 200)  # 100, 300, ..., MAX_RPS

# Path configuration (add to coordinator.py)
INTERFERENCE_SCRIPTS_DIR = "/home/george/Workspace/Interference/injection_interference"

# Interference scenarios (to be implemented)
INTERFERENCE_SCENARIOS = [
    {"id": 1, "name": "Baseline", "type": None},
    #{"id": 2, "name": "1 iBench CPU pod", "type": "ibench-cpu", "count": 1},
    #{"id": 3, "name": "2 iBench CPU pods", "type": "ibench-cpu", "count": 2},
    #{"id": 4, "name": "4 iBench CPU pods", "type": "ibench-cpu", "count": 4},
    #{"id": 5, "name": "8 iBench CPU pods", "type": "ibench-cpu", "count": 8},
    #{"id": 6, "name": "1 stress-ng l3 pod", "type": "stress-ng-l3", "count": 1},
    #{"id": 7, "name": "2 stress-ng l3 pods", "type": "stress-ng-l3", "count": 2},
    #{"id": 8, "name": "4 stress-ng l3 pods", "type": "stress-ng-l3", "count": 4},
    #{"id": 9, "name": "8 stress-ng l3 pods", "type": "stress-ng-l3", "count": 8},
    #{"id": 10, "name": "1 iBench memBW pod", "type": "ibench-membw", "count": 1}
    #{"id": 11, "name": "2 iBench memBW pods", "type": "ibench-membw", "count": 2},
    #{"id": 12, "name": "4 iBench memBW pods", "type": "ibench-membw", "count": 4},
    #{"id": 13, "name": "8 iBench memBW pods", "type": "ibench-membw", "count": 8}
]

def create_interference(scenario: Dict) -> bool:
    """Launch interference using your dedicated scripts"""
    try:
        if scenario["type"] == "ibench-cpu":
            cmd = [
                "python3", 
                f"{INTERFERENCE_SCRIPTS_DIR}/deploy_ibench_cpu_v2.py",
                str(scenario["count"])
            ]
            # Add --nginx flag for scenarios 2-4 (same-node interference)
            if scenario["id"] in [2, 3, 4]:
                cmd.append("--nginx")
        
        elif scenario["type"] == "stressng-l3":
            cmd = [
                "python3",
                f"{INTERFERENCE_SCRIPTS_DIR}/deploy_stressng_l3.py",
                str(scenario["count"])
            ]
        
        elif scenario["type"] == "ibench-membw":
            cmd = [
                "python3",
                f"{INTERFERENCE_SCRIPTS_DIR}/deploy_ibench_membw.py",
                str(scenario["count"])
            ]
        elif scenario["type"] == "mix":
            # Handle mixed scenarios
            cmd = []
            for component in scenario["components"]:
                if component["type"] == "ibench-cpu":
                    cmd.append(
                        f"python3 {INTERFERENCE_SCRIPTS_DIR}/deploy_ibench_cpu_v2.py {component['count']} --nginx"
                    )
                elif component["type"] == "stress-ng-l3":
                    cmd.append(
                        f"python3 {INTERFERENCE_SCRIPTS_DIR}/deploy_stressng_l3.py {component['count']}"
                    )
                elif component["type"] == "ibench-membw":
                    cmd.append(
                        f"python3 {INTERFERENCE_SCRIPTS_DIR}/deploy_ibench_membw.py {component['count']}"
                    )
            cmd = " && ".join(cmd)
        else:  # Baseline
            return True
            
        subprocess.run(cmd, check=True)
        time.sleep(10)  # Wait for interference to stabilize
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Interference creation failed: {e}")
        return False
    
def run_wrk_test(raw_folder: str, replicas: int, rps: int, test_id: str):
    """Execute wrk test and return parsed metrics"""
    wrk_output_file = os.path.join(raw_folder, f"wrk_output_{test_id}.txt")
    
    try:
        # Run wrk command
        with open(wrk_output_file, "w") as f:
            subprocess.run([
                WRK_PATH,
                f"-t{THREADS}",
                f"-c{CONCURRENT_CONNS}",
                f"-d{DURATION}",
                f"-R{rps}",
                "-L",
                NGINX_SERVICE_URL
            ], stdout=f, stderr=subprocess.PIPE, check=True, text=True)

        # Parse results
        with open(wrk_output_file) as f:
            output = f.read()

        return wrk_output_file

    except subprocess.CalledProcessError as e:
        print(f"wrk test failed: {e.stderr}")
        return {k: 0.0 for k in [
            "Throughput", "Avg_Latency", "P50_Latency",
            "P75_Latency", "P90_Latency", "P99_Latency", "Max_Latency"
        ]}


def ensure_directories(script_dir):
    """
    Create necessary directories for storing results and raw logs.
    Returns the paths to the baseline results directory and the raw log folder.
    """
    baseline_results_dir = os.path.join(script_dir, "NEW_V01")
    os.makedirs(baseline_results_dir, exist_ok=True)
    raw_log_folder = os.path.join(baseline_results_dir, "raw_folder")
    os.makedirs(raw_log_folder, exist_ok=True)
    return baseline_results_dir, raw_log_folder


"""
for replicas in REPLICAS_TO_TEST:                   # Outer loop
    for rps in RPS_STEPS:                           # Middle loop
        for scenario in INTERFERENCE_SCENARIOS:     # Inner loop
"""
def main():
    test_case_id = int(time.time())

    script_dir = os.path.dirname(os.path.abspath(__file__))
    baseline_results_dir, raw_log_folder = ensure_directories(script_dir)
    
    # Create timestamp and date strings for file naming and logging.
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Data Files
    pcm_raw_file = os.path.join(raw_log_folder, f"pcm_raw_{timestamp}.csv")
    pcm_system_csv = os.path.join(baseline_results_dir, f"pcm_system_{date_str}_{timestamp}.csv")
    pcm_core_csv = os.path.join(baseline_results_dir, f"pcm_core_{date_str}_{timestamp}.csv")
    # Define CSV file paths for final aggregated results.
    workload_csv = os.path.join(baseline_results_dir, "workload_metrics.csv")
    # Initialize results file
    with open(os.path.join(baseline_results_dir, "workload_metrics.csv"), "w") as f:
        csv.DictWriter(f, fieldnames=[
            "Replicas", "Interference", "Given_RPS", "Throughput",
            "Avg_Latency", "P50_Latency", "P75_Latency", 
            "P90_Latency", "P99_Latency", "Max_Latency"
        ]).writeheader()

    duration = int(DURATION[:-1]) # Convert duration to seconds and add buffer

    for replicas in REPLICAS_TO_TEST:
        # Scale NGINX once per replica count
        subprocess.run(["kubectl", "scale", "deployment", "my-nginx", f"--replicas={replicas}"], check=True)
        time.sleep(3)  # Wait for scaling

        for rps in RPS_STEPS:
            for scenario in INTERFERENCE_SCENARIOS:
                print(f"\n[Replicas={replicas}|RPS={rps}] Testing {scenario['name']}")

                # Setup interference
                if scenario["type"] and not create_interference(scenario):
                    print(f"Skipping failed scenario {scenario['name']}")
                    continue
                time.sleep(4) 
                # Generate unique test ID
                test_id = f"{test_case_id}_{scenario['id']}_{replicas}_{rps}"

                print(f"[Replicas={replicas}|RPS={rps}] Starting PCM monitoring...")
                intelpcm_thread = threading.Thread(target=pcm_monitoring, args=(duration+6, 5000, pcm_raw_file, pcm_system_csv, pcm_core_csv), daemon=True)
                intelpcm_thread.start()
                time.sleep(1)  # Give some time for the monitoring to start

                print(f"[Replicas={replicas}|RPS={rps}] Starting workload traffic...")    
                #workload_output = run_workload(hotel_reservation_script, threads, connections, duration, reqs_per_sec, wrk2_script_path_hr)
                wrk_output_file = run_wrk_test(raw_log_folder, replicas, rps, test_id="baseline")

                #Sleep for the duration of the workload
                #time.sleep(duration)
                print(f"[Replicas={replicas}|RPS={rps}] Workload traffic completed. File: {wrk_output_file}")
                end_time_str = str(int(time.time()))
                # Wait for monitoring threads to finish
                #perf_thread.join()
                #amduprof_thread.join()
                intelpcm_thread.join()
                print(f"[Replicas={replicas}|RPS={rps}] PCM monitoring completed.")
    
                #print("Coordinator: Starting Container-level monitoring...")
                #collect_container_metrics(PROMETHEUS_URL, start_time_str, end_time_str, STEP, test_case_id, interference, date_str, detail_csv_path, agg_csv_path)
                #print("Coordinator: Container-level monitoring completed.")

                print(f"[Replicas={replicas}|RPS={rps}] Parsing and storing workload output...")
                workload_metrics = parse_workload_output(wrk_output_file)
                print(f"[Replicas={replicas}|RPS={rps}] Parsed metrics: {workload_metrics}")
                store_workload_metrics(workload_csv, replicas, scenario["name"], workload_metrics, rps)

                #if scenario["type"]:
                    #cleanup_interference(scenario)

                time.sleep(SLEEP_BETWEEN_TESTS)

if __name__ == "__main__":
    main()
