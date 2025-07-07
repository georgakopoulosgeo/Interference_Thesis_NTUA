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

# Control whether to use colocation scenarios
TEST_COLOCATION = True  # Set to False to use original scenarios

# Folder Name
FOLDER_NAME = "The_Substance_V01" #Folder to store results

# Nginx service URL and paths
NGINX_SERVICE_URL = "http://192.168.49.3:30080"
WRK_PATH = "/home/george/Workspace/Interference/workloads/wrk2/wrk"
VEGETA_PATH = "vegeta"
NGINX_SCRIPT = "/home/george/Workspace/Interference/workloads/nginx/run_nginx.py"
DURATION = "3m"  # Test duration per run
THREADS = 1
CONCURRENT_CONNS = 200
# Deployment Configurations
NGINX_NODE1_DEPLOYMENT_NAME = "my-nginx-node1"
NGINX_NODE2_DEPLOYMENT_NAME = "my-nginx"
NGINX_NODE1_DEPLOY_YAML = "/home/george/Workspace/Interference/workloads/nginx/nginx-deploy-node1.yaml"
NGINX_NODE2_DEPLOY_YAML = "/home/george/Workspace/Interference/workloads/nginx/nginx-deploy.yaml"
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
# Test scenarios
REPLICAS_SCENARIOS_TO_TEST = [
    # Balanced Scenarios
    {"node1": 1, "node2": 1, "name": "balanced_1"},
    {"node1": 2, "node2": 2, "name": "balanced_2"},
    {"node1": 3, "node2": 3, "name": "balanced_3"}, 
    # Weighted Scenarios
    {"node1": 1, "node2": 2, "name": "weighted_1_2"},
    {"node1": 2, "node2": 1, "name": "weighted_2_1"},
    {"node1": 3, "node2": 1, "name": "weighted_3_1"},
    {"node1": 1, "node2": 3, "name": "weighted_1_3"},
    {"node1": 2, "node2": 3, "name": "weighted_2_3"},
    {"node1": 3, "node2": 2, "name": "weighted_3_2"},
]
RPS_STEPS = [1500]  # RPS steps to test

# Path configuration (add to coordinator.py)
INTERFERENCE_SCRIPTS_DIR = "/home/george/Workspace/Interference/injection_interference"

# Interference scenarios (to be implemented)
INTERFERENCE_SCENARIOS = [
    # Baseline Scenarios
    {"id": 0, "name": "Baseline0", "type": None},
    {"id": 1, "name": "Baseline1", "type": None},
    {"id": 2, "name": "Baseline2", "type": None},
    #{"id": 3, "name": "Baseline3", "type": None},
    #{"id": 4, "name": "Baseline4", "type": None},
    # Ibench CPU Scenarios
    {"id": 11, "name": "1_iBench_CPU_pod", "type": "ibench-cpu", "count": 1},
    {"id": 12, "name": "2_iBench_CPU_pods", "type": "ibench-cpu", "count": 2},
    {"id": 13, "name": "3_iBench_CPU_pods", "type": "ibench-cpu", "count": 3},
    {"id": 14, "name": "4_iBench_CPU_pods", "type": "ibench-cpu", "count": 4},
    # Stress-ng L3 Scenarios
    {"id": 21, "name": "1_stress-ng_l3_pod", "type": "stress-ng-l3", "count": 1},
    {"id": 22, "name": "2_stress-ng_l3_pods", "type": "stress-ng-l3", "count": 2},
    {"id": 23, "name": "3_stress-ng_l3_pods", "type": "stress-ng-l3", "count": 3},
    {"id": 24, "name": "4_stress-ng_l3_pods", "type": "stress-ng-l3", "count": 4},
    #iBench MemBW Scenarios
    {"id": 31, "name": "1_iBench_memBW_pod", "type": "ibench-membw", "count": 1},
    {"id": 32, "name": "2_iBench_memBW_pods", "type": "ibench-membw", "count": 2},
    {"id": 33, "name": "3_iBench_memBW_pods", "type": "ibench-membw", "count": 3},
    {"id": 34, "name": "4_iBench_memBW_pods", "type": "ibench-membw", "count": 4}
]

# Add this alongside your existing INTERFERENCE_SCENARIOS
INTERFERENCE_SCENARIOS_COLOCATION = [
    # Baseline Scenarios
    {"id": 200, "name": "Baseline0", "type": None},
    {"id": 201, "name": "Baseline1", "type": None},
    {"id": 202, "name": "Baseline2", "type": None},

    # Both nodes / CPU
    {"id": 212, "name": "2_iBench_CPU_both", "type": "ibench-cpu", "count": 2, "all_nodes": "both"},
    {"id": 213, "name": "3_iBench_CPU_both", "type": "ibench-cpu", "count": 3, "all_nodes": "both"},
    {"id": 214, "name": "4_iBench_CPU_both", "type": "ibench-cpu", "count": 4, "all_nodes": "both"},
    {"id": 215, "name": "5_iBench_CPU_both", "type": "ibench-cpu", "count": 5, "all_nodes": "both"},
    {"id": 216, "name": "6_iBench_CPU_both", "type": "ibench-cpu", "count": 6, "all_nodes": "both"},
    
    # Both nodes / L3
    {"id": 222, "name": "2_stress-ng_l3_both", "type": "stress-ng-l3", "count": 2, "all_nodes": "both"},
    {"id": 223, "name": "3_stress-ng_l3_both", "type": "stress-ng-l3", "count": 3, "all_nodes": "both"},
    {"id": 224, "name": "4_stress-ng_l3_both", "type": "stress-ng-l3", "count": 4, "all_nodes": "both"},
    {"id": 225, "name": "5_stress-ng_l3_both", "type": "stress-ng-l3", "count": 5, "all_nodes": "both"},
    {"id": 226, "name": "6_stress-ng_l3_both", "type": "stress-ng-l3", "count": 6, "all_nodes": "both"},

    # Both nodes / MemBW
    {"id": 232, "name": "2_iBench_memBW_both", "type": "ibench-membw", "count": 2, "all_nodes": "both"},
    {"id": 233, "name": "3_iBench_memBW_both", "type": "ibench-membw", "count": 3, "all_nodes": "both"},
    {"id": 234, "name": "4_iBench_memBW_both", "type": "ibench-membw", "count": 4, "all_nodes": "both"},
    {"id": 235, "name": "5_iBench_memBW_both", "type": "ibench-membw", "count": 5, "all_nodes": "both"},
    {"id": 236, "name": "6_iBench_memBW_both", "type": "ibench-membw", "count": 6, "all_nodes": "both"}
]

def calculate_duration():
    """Calculate the total duration of the execution"""
    total_duration = 0
    for replicas in REPLICAS_SCENARIOS_TO_TEST:
        for rps in RPS_STEPS:
            for scenario in INTERFERENCE_SCENARIOS:
                # Each test runs for DURATION + stabilization times
                total_duration += int(DURATION[:-1])*60 + STABILATION_TIME_AFTER_DEPLOYMENT + STABILATION_TIME_AFTER_DELETION + STABILATION_TIME_AFTER_INTERFERENCE + SLEEP_BETWEEN_TESTS
    print(f"Total execution duration: {total_duration} seconds", flush=True)
    print(f"Total execution duration: {total_duration / 60} minutes", flush=True)
    print(f"Total execution duration: {total_duration / 3600} hours", flush=True)


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

def create_interference_with_colocation(scenario: Dict) -> bool:
    """Handle interference creation with node colocation options"""
    if scenario["type"] is None:
        return True  # Baseline scenario
    
    # Handle "both" case by creating half on each node
    if scenario.get("all_nodes") == "both":
        half_count = max(1, scenario["count"] // 2)
        
        # Create first half on node1
        node1_scenario = scenario.copy()
        node1_scenario["count"] = half_count
        node1_scenario["all_nodes"] = True
        
        # Create remaining on node2
        node2_scenario = scenario.copy()
        node2_scenario["count"] = scenario["count"] - half_count
        node2_scenario["all_nodes"] = False
        
        return (create_interference(node1_scenario) and 
                create_interference(node2_scenario))
    
    # Use existing function for single-node cases
    return create_interference(scenario)


# WORKLOAD DEPLOYMENT, SCALING AND DELETION FUNCTIONS
def deploy_workload(yaml_file: str):
    """Generic workload deployment using kubectl"""
    try:
        subprocess.run(["kubectl", "apply", "-f", yaml_file], check=True)
        print(f"[DEPLOYMENT] Workload from {yaml_file} deployed successfully.", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to deploy workload: {e.stderr}", flush=True)   

def scale_workload(deployment_name: str, replicas: int):
    """Generic workload scaling"""
    try:
        subprocess.run(["kubectl", "scale", "deployment", deployment_name, f"--replicas={replicas}"], check=True)
        print(f"{deployment_name} scaled to {replicas} replicas successfully.", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to scale {deployment_name}: {e.stderr}", flush=True)

def delete_workload(deployment_name: str):
    """Generic workload deletion"""
    try:
        subprocess.run(["kubectl", "delete", "deployment", deployment_name], check=True)
        print(f"{deployment_name} deleted successfully.", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to delete {deployment_name}: {e.stderr}", flush=True)

def deploy_nginx_scenario(node1_replicas: int, node2_replicas: int):
    """Deploy nginx across nodes according to scenario"""
    # Deploy both deployments (they'll start with 1 replica)
    deploy_workload(NGINX_NODE1_DEPLOY_YAML)
    deploy_workload(NGINX_NODE2_DEPLOY_YAML)
    
    # Scale to desired replicas
    scale_workload(NGINX_NODE1_DEPLOYMENT_NAME, node1_replicas)
    scale_workload(NGINX_NODE2_DEPLOYMENT_NAME, node2_replicas)

def cleanup_nginx_scenario():
    """Clean up both nginx deployments"""
    delete_workload(NGINX_NODE1_DEPLOYMENT_NAME)
    delete_workload(NGINX_NODE2_DEPLOYMENT_NAME)


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

    for replicas_scenario in REPLICAS_SCENARIOS_TO_TEST:
        node1_replicas = replicas_scenario["node1"]
        node2_replicas = replicas_scenario["node2"]
        scenario_name = replicas_scenario["name"]
        
        # Skip if no replicas in scenario
        if node1_replicas == 0 and node2_replicas == 0:
            continue
        for rps in RPS_STEPS:
                        # Determine which interference scenarios to use
            interference_scenarios = (
                INTERFERENCE_SCENARIOS_COLOCATION 
                if TEST_COLOCATION 
                else INTERFERENCE_SCENARIOS
            )
            
            for scenario in interference_scenarios:
                # Generate unique test ID
                test_id = f"{scenario_name}replicas_scenario{scenario['id']}_{rps}rps"

                # Deploy NGINX workload and scale it
                # Deploy the scenario
                print(f"\n[Scenario={scenario_name}|Node1={node1_replicas}|Node2={node2_replicas}] Deploying NGINX...", flush=True)
                deploy_nginx_scenario(node1_replicas, node2_replicas)
                time.sleep(STABILATION_TIME_AFTER_DEPLOYMENT)
                time.sleep(STABILATION_TIME_AFTER_DEPLOYMENT) 

                # Setup interference (will handle 10s stabilization internally)
                print(f"\n[Replicas={scenario_name}|RPS={rps}] Testing {scenario['name']}", flush=True)
                if scenario["type"] and not create_interference(scenario):
                    # Here we have STABILATION_TIME sleep for the interference to stabilize
                    print(f"Skipping failed scenario {scenario['name']}", flush=True)
                    continue
                print(f"[Replicas={scenario_name}|RPS={rps}] Interference {scenario['name']} created successfully.", flush=True)
                if scenario["type"] == "mix":
                    time.sleep(STABILATION_TIME_MIX_SCENARIOS)  # Longer stabilization for mixed scenarios
                elif scenario["type"]:
                    time.sleep(STABILATION_TIME_AFTER_INTERFERENCE)

                # Start monitoring
                print(f"[Replicas={scenario_name}|RPS={rps}] Starting PCM monitoring...", flush=True)
                pcm_system_csv = os.path.join(main_results_dir, f"pcm_system_{test_id}.csv")
                pcm_core_csv = os.path.join(main_results_dir, f"pcm_core_{test_id}.csv")
                intelpcm_thread = threading.Thread(
                    target=pcm_monitoring,
                    args=(duration+6, 5000, pcm_raw_file, pcm_system_csv, pcm_core_csv),
                    daemon=True
                )
                # Run workload
                print(f"[Replicas={scenario_name}|RPS={rps}] Starting workload traffic...", flush=True)
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
                print(f"[Replicas={scenario_name}|RPS={rps}] PCM monitoring completed.", flush=True)

                # Parse and store workload output
                print(f"[Replicas={scenario_name}|RPS={rps}] Parsing and storing workload output...", flush=True)
                if GENERATOR == "wrk":
                    workload_metrics = parse_workload_output(output_file)
                    print(f"[Replicas={scenario_name}|RPS={rps}] Parsed metrics: {workload_metrics}", flush=True)
                    store_workload_metrics(workload_csv, scenario_name, scenario["name"], workload_metrics, rps, test_id, scenario["id"])
                elif GENERATOR == "vegeta": 
                    workload_metrics = parse_vegeta_metrics(output_file)
                    print(f"[Replicas={scenario_name}|RPS={rps}] Parsed metrics: {workload_metrics}", flush=True)
                    store_vegeta_metrics(workload_csv, scenario_name, scenario["name"], workload_metrics, rps, test_id, scenario["id"])

                if scenario["type"]:
                    cleanup_interference(scenario)

                print(f"[Replicas={scenario_name}|RPS={rps}] Cleanup completed for scenario {scenario['name']}.", flush=True)
                print(f"[Replicas={scenario_name}|RPS={rps}] Test case {test_id} completed. Waiting for {SLEEP_BETWEEN_TESTS} seconds before next test...", flush=True)

                # Delete NGINX workload if it exists
                print(f"[Replicas={scenario_name}|RPS={rps}] Deleting existing NGINX workload if any...", flush=True)
                cleanup_nginx_scenario()
                #time.sleep(STABILATION_TIME_AFTER_DELETION)  # Wait for deletion to stabilize

                time.sleep(SLEEP_BETWEEN_TESTS)
                # Clear the raw log folder for the next test
                for file in os.listdir(raw_log_folder):
                    file_path = os.path.join(raw_log_folder, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)


if __name__ == "__main__":
    run_nginx_testing()