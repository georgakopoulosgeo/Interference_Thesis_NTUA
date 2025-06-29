#!/usr/bin/env python3
import os
import csv
import datetime
import argparse
import subprocess
import time
from typing import List, Dict, Optional
from system_monitor_intepcm import pcm_monitoring
from workload_run_monitor import store_workload_metrics, parse_workload_output, parse_memtier_output, store_redis_metrics, parse_vegeta_metrics, store_vegeta_metrics
import threading


FOLDER_NAME = "bababab"  # Folder to store results

# Redis server configuration (for memtier_benchmark)
REDIS_SERVER = "192.168.49.3"
REDIS_PORT = "31020"  
MEMTIER_PATH = "/home/george/Workspace/Interference/workloads/memtier_benchmark/memtier_benchmark"
REDIS_CLIENTS = 100
REDIS_THREADS = 1
REDIS_RATIO = "2:1"  # 50% read, 50% write
REDIS_DATA_SIZE = 32  # Data size in bytes
REDIS_TEST_TIME = 60  # Test duration in seconds

# PCM monitoring configuration
SLEEP_BETWEEN_TESTS = 30                    # Sleep time between tests to allow system to stabilize
STABILATION_TIME_AFTER_DEPLOYMENT = 12      # Time to wait for system stabilization after deployment of workloads
STABILATION_TIME_AFTER_DELETION = 10        # Time to wait for system stabilization after deletion of workloads
STABILATION_TIME_AFTER_INTERFERENCE = 10    # Time to wait for system stabilization after interference deployment
STABILATION_TIME_MIX_SCENARIOS = 20         # Longer stabilization for mixed scenarios
STABILATION_TIME_AFTER_WARMUP = 10          # Time to wait for system stabilization after warmup / IGNORE
STABILATION_TIME_NEW_REPLICAS = 60          # Time to wait before tests for new replicas


# Test matrix
REPLICAS_TO_TEST = [1, 2]  # Number of replicas to test
RPS_STEPS = [1500]

# Path configuration (add to coordinator.py)
INTERFERENCE_SCRIPTS_DIR = "/home/george/Workspace/Interference/injection_interference"

# Interference scenarios (to be implemented)
INTERFERENCE_SCENARIOS = [
    # Baseline Scenarios
    {"id": 0, "name": "Baseline0", "type": None},
    #{"id": 1, "name": "Baseline1", "type": None},
    #{"id": 2, "name": "Baseline2", "type": None},
    #{"id": 3, "name": "Baseline3", "type": None},
    #{"id": 4, "name": "Baseline4", "type": None},
    # Ibench CPU Scenarios
    #{"id": 5, "name": "1_iBench_CPU_pod", "type": "ibench-cpu", "count": 1},
    {"id": 6, "name": "2_iBench_CPU_pods", "type": "ibench-cpu", "count": 2},
    #{"id": 7, "name": "3_iBench_CPU_pods", "type": "ibench-cpu", "count": 3},
    #{"id": 8, "name": "4_iBench_CPU_pods", "type": "ibench-cpu", "count": 4},
    # Stress-ng L3 Scenarios
    #{"id": 9, "name": "1_stress-ng_l3_pod", "type": "stress-ng-l3", "count": 1},
    {"id": 10, "name": "2_stress-ng_l3_pods", "type": "stress-ng-l3", "count": 2},
    #{"id": 11, "name": "3_stress-ng_l3_pods", "type": "stress-ng-l3", "count": 3},
    #{"id": 12, "name": "4_stress-ng_l3_pods", "type": "stress-ng-l3", "count": 4},
    # iBench MemBW Scenarios
    #{"id": 13, "name": "1_iBench_memBW_pod", "type": "ibench-membw", "count": 1},
    {"id": 14, "name": "2_iBench_memBW_pods", "type": "ibench-membw", "count": 2}
    #{"id": 15, "name": "3_iBench_memBW_pods", "type": "ibench-membw", "count": 3},
    #{"id": 16, "name": "4_iBench_memBW_pods", "type": "ibench-membw", "count": 4},
]

# INTERFERENCE FUNCTIONS
def create_interference(scenario: Dict, from_mix = False, all_nodes = False) -> bool:
    """Create interference pods based on the scenario.
    Returns True if successful, False otherwise."""
    if scenario["type"] == "ibench-cpu":
        script_path = os.path.join(INTERFERENCE_SCRIPTS_DIR, "deploy_ibench_cpu.py")
        try:
            # Launch interference pods (60s total: 10s stabilization + 40s test + 10s buffer)
            if not all_nodes:
                subprocess.run(
                    ["python3", script_path, str(scenario["count"]), "--nginx"],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            else:
                subprocess.run(
                    ["python3", script_path, str(scenario["count"])],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            # Wait for stabilization period (10s)
            if not from_mix:
                print("[Interference Creator] Waiting 10 seconds for system stabilization...", flush=True)
                time.sleep(STABILATION_TIME_AFTER_INTERFERENCE)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error creating interference: {e.stderr}", flush=True)
            return False
    elif scenario["type"] == "stress-ng-l3":
        script_path = os.path.join(INTERFERENCE_SCRIPTS_DIR, "deploy_ibench_l3.py")
        try:
            if not all_nodes:
                subprocess.run([
                    "python3",
                    script_path,
                    str(scenario["count"]),
                    "--nginx"
                ], check=True, capture_output=True)
            else:
                subprocess.run([
                    "python3",
                    script_path,
                    str(scenario["count"])
                ], check=True, capture_output=True)
            if not from_mix:
                print("[Interference Creator] Waiting 10 seconds for system stabilization...", flush=True)
                time.sleep(STABILATION_TIME_AFTER_INTERFERENCE)
            return True
        except subprocess.CalledProcessError as e:
            print(f"stress-ng-l3 deployment failed: {e.stderr.decode()}", flush=True)
            return False
    elif scenario["type"] == "ibench-membw":
        script_path = os.path.join(INTERFERENCE_SCRIPTS_DIR, "deploy_ibench_membw.py")
        try:
            if not all_nodes:
                subprocess.run([
                    "python3",
                    script_path,
                    str(scenario["count"]),
                    "--nginx"
                ], check=True, capture_output=True)
            else:
                subprocess.run([
                    "python3",
                    script_path,
                    str(scenario["count"])
                ], check=True, capture_output=True)
            if not from_mix:
                print("[Interference Creator] Waiting 10 seconds for system stabilization...", flush=True)
                time.sleep(STABILATION_TIME_AFTER_INTERFERENCE)
            return True
        except subprocess.CalledProcessError as e:
            print(f"ibench-membw deployment failed: {e.stderr.decode()}", flush=True)
            return False
    elif scenario["type"] == "mix":
        # Handle mixed scenarios
        for mix_scenario in scenario["mix"]:
            if not create_interference(mix_scenario, True):
                print(f"Failed to create interference for {mix_scenario['name']}", flush=True)
                return False
        print("[Interference Creator] Waiting 20 seconds for mixed scenario stabilization...", flush=True)
        time.sleep(STABILATION_TIME_MIX_SCENARIOS)
        print(f"Mixed scenario {scenario['name']} created successfully.", flush=True)
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
            os.path.join(INTERFERENCE_SCRIPTS_DIR, "cleanup_ibench_l3.py")
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

# ENSURE DIRECTORIES FUNCTION
def ensure_directories(script_dir):
    """
    Create necessary directories for storing results and raw logs.
    Returns the paths to the baseline results directory and the raw log folder.
    """
    # Main results directory
    main_results_dir = os.path.join(script_dir, FOLDER_NAME)
    os.makedirs(main_results_dir, exist_ok=True)
    
    # Create separate baseline directory
    baseline_results_dir = os.path.join(main_results_dir, "baseline_tests")
    os.makedirs(baseline_results_dir, exist_ok=True)
    
    # Raw log folder (for all tests)
    raw_log_folder = os.path.join(main_results_dir, "raw_folder")
    os.makedirs(raw_log_folder, exist_ok=True)
    
    return main_results_dir, raw_log_folder


def run_memtier_test(raw_folder: str):
    """Execute memtier_benchmark test and return output file path"""
    memtier_output_file = os.path.join(raw_folder, "memtier_output.txt")
    
    try:
        # Run memtier_benchmark command
        with open(memtier_output_file, "w") as f:
            subprocess.run([
                "memtier_benchmark",
                f"--server={REDIS_SERVER}",  
                f"--port={REDIS_PORT}",     
                "--protocol=redis",
                f"--clients={REDIS_CLIENTS}",
                f"--threads={REDIS_THREADS}",
                f"--ratio={REDIS_RATIO}",
                f"--data-size={REDIS_DATA_SIZE}",
                f"--test-time={REDIS_TEST_TIME}",
                "--print-percentiles=50,90,99,99.9"
            ], stdout=f, stderr=subprocess.PIPE, check=True, text=True)

        return memtier_output_file

    except subprocess.CalledProcessError as e:
        print(f"memtier_benchmark test failed: {e.stderr}", flush=True)
        return {k: 0.0 for k in [
            "Throughput", "Avg_Latency", "P50_Latency",
            "P90_Latency", "P99_Latency", "P99.9_Latency"
        ]}

def run_redis_testing():
    """Execute Redis benchmarking with different workload scenarios"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_results_dir, raw_log_folder = ensure_directories(script_dir)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Data Files
    pcm_raw_file = os.path.join(raw_log_folder, f"pcm_raw_{timestamp}.csv")
    
    # Redis Workload Scenarios
    REDIS_SCENARIOS = {
        "read_heavy": {"ratio": "9:1", "pipeline": 10, "clients": 50},
        "write_heavy": {"ratio": "1:9", "pipeline": 1, "clients": 30},
        "mixed": {"ratio": "1:1", "pipeline": 5, "clients": 40},
        "large_payload": {"ratio": "1:1", "data_size": 1024, "clients": 20}
    }

    # Initialize results file
    workload_csv = os.path.join(main_results_dir, "redis_metrics.csv")
    with open(workload_csv, "w") as f:
        csv.DictWriter(f, fieldnames=[
            "Test_ID", "Replicas", "Interference", "Scenario", "Throughput",
            "Avg_Latency", "P50_Latency", "P90_Latency",
            "P99_Latency", "P99.9_Latency", "Clients"
        ]).writeheader()

    duration = int(REDIS_TEST_TIME)
    prev_interference_type = None

    for replicas in REPLICAS_TO_TEST:
        subprocess.run(["kubectl", "scale", "deployment", "my-redis", f"--replicas={replicas}"], check=True)
        time.sleep(5)

        for scenario in INTERFERENCE_SCENARIOS:
            if scenario["type"] != prev_interference_type:
                #warmup_with_interference(scenario["type"])
                time.sleep(STABILATION_TIME_AFTER_WARMUP)
            prev_interference_type = scenario["type"]

            for workload_name, workload_params in REDIS_SCENARIOS.items():
                test_id = f"{replicas}replicas_scenario{scenario['id']}_{workload_name}"
                
                print(f"\n[Replicas={replicas}|Scenario={scenario['name']}|Workload={workload_name}] Starting test {test_id}")
                # Start monitoring
                pcm_system_csv = os.path.join(main_results_dir, f"pcm_system_{test_id}.csv")
                pcm_core_csv = os.path.join(main_results_dir, f"pcm_core_{test_id}.csv")
                intelpcm_thread = threading.Thread(
                    target=pcm_monitoring,
                    args=(duration+6, 5000, pcm_raw_file, pcm_system_csv, pcm_core_csv),
                    daemon=True
                )
                intelpcm_thread.start()
                time.sleep(1)

                # Run workload
                memtier_output = run_memtier_test(
                    raw_log_folder,
                    clients=workload_params["clients"],
                    threads=2,
                    ratio=workload_params.get("ratio", "1:1"),
                    data_size=workload_params.get("data_size", 32),
                    pipeline=workload_params.get("pipeline", 1),
                    test_time=duration
                )
                intelpcm_thread.join()

                # Process results
                redis_metrics = parse_memtier_output(memtier_output)
                store_redis_metrics(
                    workload_csv,
                    replicas,
                    scenario["name"],
                    workload_name,
                    redis_metrics,
                    workload_params["clients"],
                    test_id
                )

                if scenario["type"]:
                    cleanup_interference(scenario)

                time.sleep(1)
                # Clear the raw log folder for the next test
                for file in os.listdir(raw_log_folder):
                    file_path = os.path.join(raw_log_folder, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                time.sleep(SLEEP_BETWEEN_TESTS)