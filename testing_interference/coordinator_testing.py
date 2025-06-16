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
MAX_RPS = 2500  # Adjust based on your earlier findings
DURATION = "40s"  # Test duration per run
THREADS = 1
CONCURRENT_CONNS = 200
SLEEP_BETWEEN_TESTS = 20
STABILATION_TIME = 10  # Time to wait for system stabilization after interference deployment
STABILATION_TIME_MIX_SCENARIOS = 20  # Longer stabilization for mixed scenarios

# Test matrix
REPLICAS_TO_TEST = range(1, 6)  # 1-5 replicas
RPS_STEPS = range(100, MAX_RPS + 1, 400)  # 100, 500, 900, 1300, 1700, 2100, 2500
# 80seconds per test case / 22 Scenarios / 5 Replicas / 7 RPS steps
# Program will run for 80 * 22 * 5 * 7 =  61600 seconds (approximately 17 hours) 

# Path configuration (add to coordinator.py)
INTERFERENCE_SCRIPTS_DIR = "/home/george/Workspace/Interference/injection_interference"

# Interference scenarios (to be implemented)
INTERFERENCE_SCENARIOS = [
    # Baseline Scenarios
    {"id": 0, "name": "Baseline0", "type": None},
    {"id": 1, "name": "Baseline1", "type": None},
    # Ibench CPU Scenarios
    {"id": 2, "name": "1_iBench_CPU_pod", "type": "ibench-cpu", "count": 1},
    {"id": 3, "name": "2_iBench_CPU_pods", "type": "ibench-cpu", "count": 2},
    {"id": 4, "name": "4_iBench_CPU_pods", "type": "ibench-cpu", "count": 4},
    {"id": 5, "name": "8_iBench_CPU_pods", "type": "ibench-cpu", "count": 8},
    # Stress-ng L3 Scenarios
    {"id": 6, "name": "1_stress-ng_l3_pod", "type": "stress-ng-l3", "count": 1},
    {"id": 7, "name": "2_stress-ng_l3_pods", "type": "stress-ng-l3", "count": 2},
    {"id": 8, "name": "4_stress-ng_l3_pods", "type": "stress-ng-l3", "count": 4},
    {"id": 9, "name": "8_stress-ng_l3_pods", "type": "stress-ng-l3", "count": 8},
    # iBench MemBW Scenarios
    {"id": 10, "name": "1_iBench_memBW_pod", "type": "ibench-membw", "count": 1},
    {"id": 11, "name": "2_iBench_memBW_pods", "type": "ibench-membw", "count": 2},
    {"id": 12, "name": "4_iBench_memBW_pods", "type": "ibench-membw", "count": 4},
    {"id": 13, "name": "8_iBench_memBW_pods", "type": "ibench-membw", "count": 8}
]


def create_interference(scenario: Dict, from_mix = False) -> bool:
    """Create interference pods based on the scenario.
    Returns True if successful, False otherwise."""

    if scenario["type"] == "ibench-cpu":
        script_path = os.path.join(INTERFERENCE_SCRIPTS_DIR, "deploy_ibench_cpu_v2.py")
        try:
            # Launch interference pods (60s total: 10s stabilization + 40s test + 10s buffer)
            subprocess.run(
                ["python3", script_path, str(scenario["count"]), "--nginx"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for stabilization period (10s)
            if not from_mix:
                print("[Interference Creator] Waiting 10 seconds for system stabilization...")
                time.sleep(STABILATION_TIME)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error creating interference: {e.stderr}")
            return False
    elif scenario["type"] == "stress-ng-l3":
        try:
            subprocess.run([
                "python3",
                os.path.join(INTERFERENCE_SCRIPTS_DIR, "deploy_stressng_l3.py"),
                str(scenario["count"])
            ], check=True, capture_output=True)
            if not from_mix:
                print("[Interference Creator] Waiting 10 seconds for system stabilization...")
                time.sleep(STABILATION_TIME)  # Wait for stabilization
            return True
        except subprocess.CalledProcessError as e:
            print(f"stress-ng-l3 deployment failed: {e.stderr.decode()}")
            return False
    elif scenario["type"] == "ibench-membw":
        try:
            subprocess.run([
                "python3",
                os.path.join(INTERFERENCE_SCRIPTS_DIR, "deploy_ibench_membw.py"),
                str(scenario["count"])
            ], check=True, capture_output=True)
            if not from_mix:
                print("[Interference Creator] Waiting 10 seconds for system stabilization...")
                time.sleep(STABILATION_TIME)  # Wait for stabilization
            return True
        except subprocess.CalledProcessError as e:
            print(f"ibench-membw deployment failed: {e.stderr.decode()}")
            return False
    elif scenario["type"] == "mix":
        # Handle mixed scenarios
        for mix_scenario in scenario["mix"]:
            if not create_interference(mix_scenario, True):
                print(f"Failed to create interference for {mix_scenario['name']}")
                return False
        print("[Interference Creator] Waiting 20 seconds for mixed scenario stabilization...")
        time.sleep(STABILATION_TIME_MIX_SCENARIOS)
        print(f"Mixed scenario {scenario['name']} created successfully.")
    return True

def cleanup_interference(scenario: Dict):
    """Clean up using separate process"""
    if scenario["type"] == "ibench-cpu":
        subprocess.run([
            "python3",
            os.path.join(INTERFERENCE_SCRIPTS_DIR, "cleanup_ibench.py")
        ], capture_output=True)
    elif scenario["type"] == "stress-ng-l3":
        subprocess.run([
            "python3",
            os.path.join(INTERFERENCE_SCRIPTS_DIR, "cleanup_stressng_l3.py")
        ], capture_output=True)
    elif scenario["type"] == "ibench-membw":
        subprocess.run([
            "python3",
            os.path.join(INTERFERENCE_SCRIPTS_DIR, "cleanup_ibench_membw.py")
        ], capture_output=True)
    elif scenario["type"] == "mix":
        # Handle mixed scenarios
        for mix_scenario in scenario["mix"]:
            cleanup_interference(mix_scenario)
    
    
def run_wrk_test(raw_folder: str, rps: int,):
    """Execute wrk test and return parsed metrics"""
    wrk_output_file = os.path.join(raw_folder, f"wrk_output.txt")
    
    try:
        # Run wrk command
        with open(wrk_output_file, "w") as f:
            subprocess.run([
                "taskset", "-c", "6,7",  # Use cores 0-3 for the test
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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    baseline_results_dir, raw_log_folder = ensure_directories(script_dir)
    
    # Create timestamp and date strings for file naming and logging.
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Data Files
    pcm_raw_file = os.path.join(raw_log_folder, f"pcm_raw_{timestamp}.csv")
    # Define CSV file paths for final aggregated results.
    workload_csv = os.path.join(baseline_results_dir, "workload_metrics.csv")
    # Initialize results file
    with open(os.path.join(baseline_results_dir, "workload_metrics.csv"), "w") as f:
        csv.DictWriter(f, fieldnames=[
            "Test_ID","Replicas", "Interference", "Given_RPS", "Throughput",
            "Avg_Latency", "P50_Latency", "P75_Latency", 
            "P90_Latency", "P99_Latency", "Max_Latency"
        ]).writeheader()

    duration = int(DURATION[:-1]) # Convert duration to seconds and add buffer

    for replicas in REPLICAS_TO_TEST:
        # Scale NGINX once per replica count
        subprocess.run(["kubectl", "scale", "deployment", "my-nginx", f"--replicas={replicas}"], check=True)
        time.sleep(3)  # Wait for scaling

        for scenario in INTERFERENCE_SCENARIOS:
            for rps in RPS_STEPS:
                print(f"\n[Replicas={replicas}|RPS={rps}] Testing {scenario['name']}")

                # Setup interference (will handle 10s stabilization internally)
                if scenario["type"] and not create_interference(scenario):
                    print(f"Skipping failed scenario {scenario['name']}")
                    continue
                # Generate unique test ID
                test_id = f"{replicas}replicas_scenario{scenario['id']}_{rps}rps"

                print(f"[Replicas={replicas}|RPS={rps}] Starting PCM monitoring...")
                pcm_system_csv = os.path.join(baseline_results_dir, f"pcm_system_{test_id}.csv")
                pcm_core_csv = os.path.join(baseline_results_dir, f"pcm_core_{test_id}.csv")
                intelpcm_thread = threading.Thread(target=pcm_monitoring, args=(duration+6, 5000, pcm_raw_file, pcm_system_csv, pcm_core_csv), daemon=True)
                intelpcm_thread.start()
                time.sleep(1)  # Give some time for the monitoring to start

                print(f"[Replicas={replicas}|RPS={rps}] Starting workload traffic...")    
                #workload_output = run_workload(hotel_reservation_script, threads, connections, duration, reqs_per_sec, wrk2_script_path_hr)
                wrk_output_file = run_wrk_test(raw_log_folder, rps)

                #Sleep for the duration of the workload
                #time.sleep(duration)
                print(f"[Replicas={replicas}|RPS={rps}] Workload traffic completed. File: {wrk_output_file}")
                # Wait for monitoring threads to finish
                #perf_thread.join()
                #amduprof_thread.join()
                intelpcm_thread.join(timeout=7)
                print(f"[Replicas={replicas}|RPS={rps}] PCM monitoring completed.")
    
                #print("Coordinator: Starting Container-level monitoring...")
                #collect_container_metrics(PROMETHEUS_URL, start_time_str, end_time_str, STEP, test_case_id, interference, date_str, detail_csv_path, agg_csv_path)
                #print("Coordinator: Container-level monitoring completed.")

                print(f"[Replicas={replicas}|RPS={rps}] Parsing and storing workload output...")
                workload_metrics = parse_workload_output(wrk_output_file)
                print(f"[Replicas={replicas}|RPS={rps}] Parsed metrics: {workload_metrics}")
                store_workload_metrics(workload_csv, replicas, scenario["name"], workload_metrics, rps, test_id)

                if scenario["type"]:
                    cleanup_interference(scenario)

                print(f"[Replicas={replicas}|RPS={rps}] Cleanup completed for scenario {scenario['name']}.")
                print(f"[Replicas={replicas}|RPS={rps}] Test case {test_id} completed. Waiting for {SLEEP_BETWEEN_TESTS} seconds before next test...")
                time.sleep(SLEEP_BETWEEN_TESTS)

                # Clear the raw log folder for the next test
                for file in os.listdir(raw_log_folder):
                    file_path = os.path.join(raw_log_folder, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)

if __name__ == "__main__":
    main()