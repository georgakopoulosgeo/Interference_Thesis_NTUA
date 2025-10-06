#!/usr/bin/env python3
import os
import csv
import datetime
import argparse
import subprocess
import time
from typing import List, Dict, Optional, Any
from system_monitor_intepcm import pcm_monitoring
from workload_run_monitor import store_workload_metrics, parse_workload_output, parse_memtier_output, store_redis_metrics, parse_vegeta_metrics, store_vegeta_metrics
import threading
import json

# Which Traffic Workload to use
GENERATOR = "vegeta"  # Options: "wrk", "vegeta"

# Folder Name
FOLDER_NAME = "TheGame_V02" #Folder to store results

# Nginx service URL and paths
NGINX_SERVICE_URL = "http://192.168.49.3:30080"
WRK_PATH = "/home/george/Workspace/Interference/workloads/wrk2/wrk"
VEGETA_PATH = "vegeta"
NGINX_SCRIPT = "/home/george/Workspace/Interference/workloads/nginx/run_nginx.py"
DURATION = "3m"  # Test duration per run
THREADS = 1
CONCURRENT_CONNS = 200
NGINX_DEPLOY_YAML = "/home/george/Workspace/Interference/workloads/nginx/nginx-deploy.yaml"
NGINX_DEPLOYMENT_NAME = "my-nginx"
NGINX_METRICS_FIELDNAMES = [
    "Test_ID", "Replicas", "Interference_Name", "Interference_ID", "Given_RPS",
    "Throughput", "Avg_Latency", "P50_Latency", "P75_Latency",
    "P90_Latency", "P95_Latency", "P99_Latency", "Max_Latency", "Errors"
]

# PCM monitoring configuration
STABILATION_TIME_AFTER_DELETION = 10        # Time to wait for system stabilization after deletion of workloads
STABILATION_TIME_AFTER_DEPLOYMENT = 10      # Time to wait for system stabilization after deployment of workloads
STABILATION_TIME_AFTER_INTERFERENCE = 10     # Time to wait for system stabilization of interference pods
SLEEP_BETWEEN_TESTS = 30                    # Sleep time between tests to allow system to stabilize

STABILATION_TIME_MIX_SCENARIOS = 12         # Longer stabilization for mixed scenarios
STABILATION_TIME_AFTER_WARMUP = 10          # Time to wait for system stabilization after warmup / IGNORE
STABILATION_TIME_NEW_REPLICAS = 22          # Time to wait before tests for new replicas

# Test matrix
REPLICAS_TO_TEST = [1,2,3,4]  # Number of replicas to test
RPS_STEPS = [100, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000]  # RPS steps to test

# Path configuration (add to coordinator.py)
INTERFERENCE_SCRIPTS_DIR = "/home/george/Workspace/Interference/injection_interference"

# Interference scenarios (to be implemented)
######
######  SOS: THE L3 SCENARIOS HAVE MAY HAVE stress-ng-l3, IN THEIR NAMES BUT WE ENDED UP USING ONLY IBENCH PODS. 
######
INTERFERENCE_SCENARIOS = [
    # Baseline Scenarios
    {"id": 0, "name": "Baseline0", "type": None},
    {"id": 1, "name": "Baseline1", "type": None},
    {"id": 2, "name": "Baseline2", "type": None},
    # Ibench CPU Scenarios
    {"id": 11, "name": "1_iBench_CPU_pod", "type": "ibench-cpu", "count": 1},
    {"id": 12, "name": "2_iBench_CPU_pods", "type": "ibench-cpu", "count": 2},
    {"id": 13, "name": "3_iBench_CPU_pods", "type": "ibench-cpu", "count": 3},
    {"id": 14, "name": "4_iBench_CPU_pods", "type": "ibench-cpu", "count": 4},
    # Stress-ng L3 Scenarios
    {"id": 21, "name": "1_stress-ng_l3_pod", "type": "ibench-l3", "count": 1},
    {"id": 22, "name": "2_stress-ng_l3_pods", "type": "ibench-l3", "count": 2},
    {"id": 23, "name": "3_stress-ng_l3_pods", "type": "ibench-l3", "count": 3},
    {"id": 24, "name": "4_stress-ng_l3_pods", "type": "ibench-l3", "count": 4},
    #iBench MemBW Scenarios
    {"id": 31, "name": "1_iBench_memBW_pod", "type": "ibench-membw", "count": 1},
    {"id": 32, "name": "2_iBench_memBW_pods", "type": "ibench-membw", "count": 2},
    {"id": 33, "name": "3_iBench_memBW_pods", "type": "ibench-membw", "count": 3},
    {"id": 34, "name": "4_iBench_memBW_pods", "type": "ibench-membw", "count": 4}
]

INTERFERENCE_SCENARIOS_MIX = [
    {"id": 51, "name": "1_CPU_1_L3", "type": "mix", "mix": [
        {"type": "ibench-cpu", "count": 1},
        {"type": "ibench-l3", "count": 1}
    ]},
    {"id": 52, "name": "1_CPU_1_MemBW", "type": "mix", "mix": [
        {"type": "ibench-cpu", "count": 1},
        {"type": "ibench-membw", "count": 1}
    ]},
    {"id": 53, "name": "1_CPU_2_MemBW", "type": "mix", "mix": [
        {"type": "ibench-cpu", "count": 1},
        {"type": "ibench-membw", "count": 2}
    ]},
    {"id": 54, "name": "2_CPU_1_MemBW", "type": "mix", "mix": [
        {"type": "ibench-cpu", "count": 2},
        {"type": "ibench-membw", "count": 1}
    ]},
    {"id": 55, "name": "1_CPU_2_L3", "type": "mix", "mix": [
        {"type": "ibench-cpu", "count": 1},
        {"type": "ibench-l3", "count": 2}
    ]},
    {"id": 56, "name": "1_CPU_1_L3_1_MemBW", "type": "mix", "mix": [
        {"type": "ibench-cpu", "count": 1},
        {"type": "ibench-l3", "count": 1},
        {"type": "ibench-membw", "count": 1}
    ]},
    {"id": 57, "name": "2_CPU_1_L3", "type": "mix", "mix": [
        {"type": "ibench-cpu", "count": 2},
        {"type": "ibench-l3", "count": 1}
    ]},
    {"id": 58, "name": "1_L3_3_MemBW", "type": "mix", "mix": [
        {"type": "ibench-l3", "count": 1},
        {"type": "ibench-membw", "count": 3}
    ]}
]

def calculate_duration():
    """Calculate the total duration of the execution"""
    total_duration = 0
    for replicas in REPLICAS_TO_TEST:
        for rps in RPS_STEPS:
            for scenario in INTERFERENCE_SCENARIOS:
                # Each test runs for DURATION + stabilization times
                total_duration += int(DURATION[:-1])*60 + STABILATION_TIME_AFTER_DEPLOYMENT + STABILATION_TIME_AFTER_DELETION + STABILATION_TIME_AFTER_INTERFERENCE + SLEEP_BETWEEN_TESTS
    print(f"Total execution duration: {total_duration} seconds", flush=True)
    print(f"Total execution duration: {total_duration / 60} minutes", flush=True)
    print(f"Total execution duration: {total_duration / 3600} hours", flush=True)


## WARMUP - IGNORE
# Warmup configuration
WARMUP_DURATION = "30s"
WARMUP_RPS = 1500
WARMUP_THREADS = 1
WARMUP_CONNECTIONS = 200
WARMUP_CLIENTS = 100
WARMUP_SCENARIOS = {
    "ibench-cpu": {"id": -1, "name": "WARMUP_CPU", "type": "ibench-cpu", "count": 1},
    "ibench-l3": {"id": -2, "name": "WARMUP_L3", "type": "ibench-l3", "count": 1},
    "ibench-membw": {"id": -3, "name": "WARMUP_MEMBW", "type": "ibench-membw", "count": 1}
}

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

def run_warmup(rps: int):
    """Run warmup workload without PCM monitoring"""
    print(f"Starting warmup at {rps} RPS equivalent...", flush=True)
    try:
        subprocess.run([
            WRK_PATH,
            f"-t{WARMUP_THREADS}",
            f"-c{WARMUP_CONNECTIONS}",
            f"-d{WARMUP_DURATION}",
            f"-R{rps}",
            NGINX_SERVICE_URL
        ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        print("Warmup completed", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"Warmup failed: {e.stderr}", flush=True)

def warmup_with_interference(interference_type: str, rps: int):
    """Run warmup with specific interference type"""
    if interference_type in WARMUP_SCENARIOS:
        print(f"Starting {interference_type} warmup...", flush=True)
        create_interference(WARMUP_SCENARIOS[interference_type])
        warmup_rps = rps
        run_warmup(warmup_rps)
        cleanup_interference(WARMUP_SCENARIOS[interference_type])
        time.sleep(STABILATION_TIME_AFTER_INTERFERENCE)

# INTERFERENCE FUNCTIONS
def create_interference(scenario: Dict, from_mix = False, all_nodes = True) -> bool:
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
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error creating interference: {e.stderr}", flush=True)
            return False
    elif scenario["type"] == "ibench-l3":
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
            return True
        except subprocess.CalledProcessError as e:
            print(f"ibench-l3 deployment failed: {e.stderr.decode()}", flush=True)
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
        print(f"Mixed scenario {scenario['name']} created successfully.", flush=True)
    return True

def cleanup_interference(scenario: Dict):
    """Clean up using separate process"""
    if scenario["type"] == "ibench-cpu":
        subprocess.run([
            "python3",
            os.path.join(INTERFERENCE_SCRIPTS_DIR, "cleanup_ibench.py")
        ], capture_output=True)
    elif scenario["type"] == "ibench-l3":
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


# WORKLOAD DEPLOYMENT, SCALING AND DELETION FUNCTIONS
def deploy_nginx_workload():
    """Deploy NGINX workload using kubectl"""
    try:
        subprocess.run(["kubectl", "apply", "-f", NGINX_DEPLOY_YAML], check=True)
        print("[DEPLOYMENT] NGINX workload deployed successfully.", flush=True)

    except subprocess.CalledProcessError as e:
        print(f"Failed to deploy NGINX workload: {e.stderr}", flush=True)   

def scale_nginx_workload(replicas: int):
    """Scale NGINX workload to a specific number of replicas"""
    try:
        subprocess.run(["kubectl", "scale", "deployment", NGINX_DEPLOYMENT_NAME, f"--replicas={replicas}"], check=True)
        print(f"NGINX workload scaled to {replicas} replicas successfully.", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to scale NGINX workload: {e.stderr}", flush=True)

def delete_nginx_workload():
    """Delete NGINX workload using kubectl"""
    try:
        subprocess.run(["kubectl", "delete", "deployment", NGINX_DEPLOYMENT_NAME], check=True)
        print("NGINX workload deleted successfully.", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to delete NGINX workload: {e.stderr}", flush=True)


# WORKLOAD TESTING FUNCTIONS
def run_wrk_test(raw_folder: str, rps: int,):
    """Execute wrk test and return parsed metrics"""
    wrk_output_file = os.path.join(raw_folder, f"wrk_output.txt")
    
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
        print(f"wrk test failed: {e.stderr}", flush=True)
        return {k: 0.0 for k in [
            "Throughput", "Avg_Latency", "P50_Latency",
            "P75_Latency", "P90_Latency", "P99_Latency", "Max_Latency"
        ]}

def run_vegeta_test(raw_folder: str, rps: int) -> Dict[str, Any]:
    """Execute Vegeta test and return parsed metrics"""
    targets_path = os.path.join(raw_folder, "vegeta_targets.txt")
    results_path = os.path.join(raw_folder, "vegeta_results.bin")
    report_path = os.path.join(raw_folder, "vegeta_report.json")
    post_body_path = os.path.join(raw_folder, "post_body.json")
    
    try:
        # Write target
        with open(targets_path, "w") as f:
            f.write(f"GET {NGINX_SERVICE_URL}")

        # Run vegeta attack
        subprocess.run([
            VEGETA_PATH, "attack",
            "-rate", str(rps),
            "-duration", DURATION,
            "-targets", targets_path,
            "-output", results_path
        ], check=True)

        # Run vegeta report
        with open(report_path, "w") as f:
            subprocess.run([
                VEGETA_PATH, "report",
                "-type=json",
                results_path
            ], stdout=f, check=True)

        # Load report
        with open(report_path) as f:
            return json.load(f)

    except subprocess.CalledProcessError as e:
        print(f"vegeta test failed: {e}", flush=True)
        return {}

    finally:
        for f in [targets_path, results_path, report_path]:
            if os.path.exists(f):
                os.remove(f)

"""
for replicas in REPLICAS_TO_TEST:                   # Outer loop
    time.sleep(STABILATION_TIME_NEW_REPLICAS)                           # Wait for new replicas to stabilize
    for rps in RPS_STEPS:                           # Middle loop
        for scenario in INTERFERENCE_SCENARIOS:     # Inner loop
            time.sleep(STABILATION_TIME_AFTER_DELETION)                 # Wait for deletion to stabilize         
            time.sleep(STABILATION_TIME_AFTER_DEPLOYMENT)               # Wait for deployment to stabilize
            time.sleep(STABILATION_TIME_AFTER_INTERFERENCE)             # Wait for interference to stabilize
            workload duration                                           # Duration of the workload test
            time.sleep(SLEEPBETWEEN_TESTS)                              # Sleep between tests
"""

def run_nginx_testing():
    """Execute full NGINX benchmarking with RPS scaling"""

    # Calculate Duration of the whole Execution
    calculate_duration()

    # Ensure directories are set up
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_results_dir, raw_log_folder = ensure_directories(script_dir)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Data Files
    pcm_raw_file = os.path.join(raw_log_folder, f"pcm_raw_{timestamp}.csv")
    
    # Initialize results file
    workload_csv = os.path.join(main_results_dir, "nginx_metrics.csv")
    with open(workload_csv, "w") as f:
        csv.DictWriter(f, fieldnames=NGINX_METRICS_FIELDNAMES).writeheader()

    duration = int(DURATION[:-1])* 60  # Convert duration to seconds
    print(f"Total test duration: {duration} seconds", flush=True)
    prev_interference_type = None
    prev_replicas = 1

    for replicas in REPLICAS_TO_TEST:
        if replicas != prev_replicas:
            time.sleep(STABILATION_TIME_NEW_REPLICAS)
            prev_replicas = replicas
        for rps in RPS_STEPS:
            for scenario in INTERFERENCE_SCENARIOS:
                # Generate unique test ID
                test_id = f"{replicas}replicas_scenario{scenario['id']}_{rps}rps"

                # Deploy NGINX workload and scale it
                print(f"\n[Replicas={replicas}|RPS={rps}] Deploying NGINX workload...", flush=True)
                deploy_nginx_workload()
                scale_nginx_workload(replicas)
                time.sleep(STABILATION_TIME_AFTER_DEPLOYMENT) 

                # Warmup phase / IGNORE
                if scenario["type"] == None:
                    print(f"\n[Replicas={replicas}|RPS={rps}] Running warmup for baseline scenario ...", flush=True)
                    #run_warmup(rps)
                    #time.sleep(STABILATION_TIME_AFTER_WARMUP)
                elif scenario["type"] != prev_interference_type:
                    print(f"\n[Replicas={replicas}|RPS={rps}] Running warmup for {scenario['name']}...", flush=True)
                    #warmup_with_interference(scenario["type"], rps)
                    #time.sleep(STABILATION_TIME_AFTER_WARMUP)
                prev_interference_type = scenario["type"]

                # Setup interference (will handle 10s stabilization internally)
                print(f"\n[Replicas={replicas}|RPS={rps}] Testing {scenario['name']}", flush=True)
                if scenario["type"] and not create_interference(scenario):
                    # Here we have STABILATION_TIME sleep for the interference to stabilize
                    print(f"Skipping failed scenario {scenario['name']}", flush=True)
                    continue
                print(f"[Replicas={replicas}|RPS={rps}] Interference {scenario['name']} created successfully.", flush=True)
                if scenario["type"] == "mix":
                    time.sleep(STABILATION_TIME_MIX_SCENARIOS)  # Longer stabilization for mixed scenarios
                elif scenario["type"]:
                    time.sleep(STABILATION_TIME_AFTER_INTERFERENCE)

                # Start monitoring
                print(f"[Replicas={replicas}|RPS={rps}] Starting PCM monitoring...", flush=True)
                pcm_system_csv = os.path.join(main_results_dir, f"pcm_system_{test_id}.csv")
                pcm_core_csv = os.path.join(main_results_dir, f"pcm_core_{test_id}.csv")
                intelpcm_thread = threading.Thread(
                    target=pcm_monitoring,
                    args=(duration+6, 5000, pcm_raw_file, pcm_system_csv, pcm_core_csv),
                    daemon=True
                )
                # Run workload
                print(f"[Replicas={replicas}|RPS={rps}] Starting workload traffic...", flush=True)
                intelpcm_thread.start()
                time.sleep(1)
                if GENERATOR == "wrk":
                    output_file = run_wrk_test(raw_log_folder, rps)
                elif GENERATOR == "vegeta":
                    output_file = run_vegeta_test(raw_log_folder, rps)

                # Wait for monitoring threads to finish
                #perf_thread.join()
                #amduprof_thread.join()
                intelpcm_thread.join()
                time.sleep(1)  # Ensure all threads are done before proceeding
                print(f"[Replicas={replicas}|RPS={rps}] PCM monitoring completed.", flush=True)

                # Parse and store workload output
                print(f"[Replicas={replicas}|RPS={rps}] Parsing and storing workload output...", flush=True)
                if GENERATOR == "wrk":
                    workload_metrics = parse_workload_output(output_file)
                    print(f"[Replicas={replicas}|RPS={rps}] Parsed metrics: {workload_metrics}", flush=True)
                    store_workload_metrics(workload_csv, replicas, scenario["name"], workload_metrics, rps, test_id, scenario["id"])
                elif GENERATOR == "vegeta": 
                    workload_metrics = parse_vegeta_metrics(output_file)
                    print(f"[Replicas={replicas}|RPS={rps}] Parsed metrics: {workload_metrics}", flush=True)
                    store_vegeta_metrics(workload_csv, replicas, scenario["name"], workload_metrics, rps, test_id, scenario["id"])

                if scenario["type"]:
                    cleanup_interference(scenario)

                print(f"[Replicas={replicas}|RPS={rps}] Cleanup completed for scenario {scenario['name']}.", flush=True)
                print(f"[Replicas={replicas}|RPS={rps}] Test case {test_id} completed. Waiting for {SLEEP_BETWEEN_TESTS} seconds before next test...", flush=True)

                # Delete NGINX workload if it exists
                print(f"[Replicas={replicas}|RPS={rps}] Deleting existing NGINX workload if any...", flush=True)
                delete_nginx_workload()
                #time.sleep(STABILATION_TIME_AFTER_DELETION)  # Wait for deletion to stabilize

                time.sleep(SLEEP_BETWEEN_TESTS)
                # Clear the raw log folder for the next test
                for file in os.listdir(raw_log_folder):
                    file_path = os.path.join(raw_log_folder, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)


if __name__ == "__main__":
    run_nginx_testing()