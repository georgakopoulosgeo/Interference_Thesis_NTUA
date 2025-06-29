#!/usr/bin/env python3
import os
import csv
import datetime
import argparse
import subprocess
import time
from typing import List, Dict, Optional
from system_monitor_intepcm import pcm_monitoring
from workload_run_monitor import store_workload_metrics, parse_workload_output, parse_memtier_output, store_redis_metrics
import threading

# Which workload to test
WORKLOAD = "nginx"  # Options: "nginx", "redis"

# Folder Name
FOLDER_NAME = "Chaos_V02"  # Folder to store results

# Nginx service URL and paths
NGINX_SERVICE_URL = "http://192.168.49.3:30080"
WRK_PATH = "/home/george/Workspace/Interference/workloads/wrk2/wrk"
NGINX_SCRIPT = "/home/george/Workspace/Interference/workloads/nginx/run_nginx.py"
DURATION = "4m"  # Test duration per run
THREADS = 1
CONCURRENT_CONNS = 200
NGINX_DEPLOY_YAML = "/home/george/Workspace/Interference/workloads/nginx/nginx-deploy.yaml"
NGINX_DEPLOYMENT_NAME = "my-nginx"

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

# Case B Scenarios
INTERFERENCE_SCENARIOS_B = [
    # Baseline Scenarios
    {"id": 100, "name": "BaselineB0", "type": None},
    #{"id": 101, "name": "BaselineB1", "type": None},
    #{"id": 102, "name": "BaselineB2", "type": None},
    #{"id": 103, "name": "BaselineB3", "type": None},
    # iBench CPU Scenarios
    #{"id": 104, "name": "1_iBench_CPU_pod_B", "type": "ibench-cpu", "count": 1},
    {"id": 105, "name": "2_iBench_CPU_pods_B", "type": "ibench-cpu", "count": 2},
    #{"id": 106, "name": "3_iBench_CPU_pods_B", "type": "ibench-cpu", "count": 3},
    #{"id": 107, "name": "4_iBench_CPU_pods_B", "type": "ibench-cpu", "count": 4},
    # Stress-ng L3 Scenarios
    #{"id": 108, "name": "1_stress-ng_l3_pod_B", "type": "stress-ng-l3", "count": 1},
    {"id": 109, "name": "2_stress-ng_l3_pods_B", "type": "stress-ng-l3", "count": 2},
    #{"id": 110, "name": "3_stress-ng_l3_pods_B", "type": "stress-ng-l3", "count": 3},
    #{"id": 111, "name": "4_stress-ng_l3_pods_B", "type": "stress-ng-l3", "count": 4},
    # iBench MemBW Scenarios
    #{"id": 112, "name": "1_iBench_memBW_pod_B", "type": "ibench-membw", "count": 1},
    {"id": 113, "name": "2_iBench_memBW_pods_B", "type": "ibench-membw", "count": 2}
    #{"id": 114, "name": "3_iBench_memBW_pods_B", "type": "ibench-membw", "count": 3},
    #{"id": 115, "name": "4_iBench_memBW_pods_B", "type": "ibench-membw", "count": 4},
]

## WARMUP - IGNORE
# Warmup configuration
WARMUP_DURATION = "30s"
WARMUP_RPS = 1500
WARMUP_THREADS = 1
WARMUP_CONNECTIONS = 200
WARMUP_CLIENTS = 100
WARMUP_SCENARIOS = {
    "ibench-cpu": {"id": -1, "name": "WARMUP_CPU", "type": "ibench-cpu", "count": 1},
    "stress-ng-l3": {"id": -2, "name": "WARMUP_L3", "type": "stress-ng-l3", "count": 1},
    "ibench-membw": {"id": -3, "name": "WARMUP_MEMBW", "type": "ibench-membw", "count": 1}
}

def run_warmup(rps: int):
    """Run warmup workload without PCM monitoring"""
    print(f"Starting warmup at {rps} RPS equivalent...", flush=True)
    try:
        if WORKLOAD == "nginx":
            subprocess.run([
                WRK_PATH,
                f"-t{WARMUP_THREADS}",
                f"-c{WARMUP_CONNECTIONS}",
                f"-d{WARMUP_DURATION}",
                f"-R{rps}",
                NGINX_SERVICE_URL
            ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        else:  # redis
            subprocess.run([
                "memtier_benchmark",
                f"--server={REDIS_SERVER}",
                f"--port={REDIS_PORT}",
                "--protocol=redis",
                f"--clients={WARMUP_CLIENTS}",  # Should define this constant
                f"--threads={WARMUP_THREADS}",
                f"--ratio={REDIS_RATIO}",  # Should define this constant
                f"--data-size={REDIS_DATA_SIZE}",  # Should define this constant
                f"--test-time={WARMUP_DURATION[:-1]}",  # Remove 's' suffix if present
                "--print-percentiles=50,90,99"
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
        script_path = os.path.join(INTERFERENCE_SCRIPTS_DIR, "deploy_stressng_l3.py")
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

# INTERFERENCE FUNCTIONS FOR CASE B


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
        time.sleep(STABILATION_TIME_AFTER_DEPLOYMENT)  # Wait for stabilization
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

"""
for replicas in REPLICAS_TO_TEST:                   # Outer loop
    for rps in RPS_STEPS:                           # Middle loop
        for scenario in INTERFERENCE_SCENARIOS:     # Inner loop
"""

def run_nginx_testing():
    """Execute full NGINX benchmarking with RPS scaling"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_results_dir, raw_log_folder = ensure_directories(script_dir)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Data Files
    pcm_raw_file = os.path.join(raw_log_folder, f"pcm_raw_{timestamp}.csv")
    
    # Initialize results file
    workload_csv = os.path.join(main_results_dir, "nginx_metrics.csv")
    with open(workload_csv, "w") as f:
        csv.DictWriter(f, fieldnames=[
            "Test_ID", "Replicas", "Interference_Name", "Interference_ID", "Given_RPS", "Throughput",
            "Avg_Latency", "P50_Latency", "P75_Latency", 
            "P90_Latency", "P99_Latency", "Max_Latency"
        ]).writeheader()

    duration = int(DURATION[:-1])
    prev_interference_type = None
    prev_replicas = 1

    for replicas in REPLICAS_TO_TEST:
        if replicas != prev_replicas:
            time.sleep(STABILATION_TIME_NEW_REPLICAS)
        for rps in RPS_STEPS:
            for scenario in INTERFERENCE_SCENARIOS:
                # Generate unique test ID
                test_id = f"{replicas}replicas_scenario{scenario['id']}_{rps}rps"
                
                # Delete NGINX workload if it exists
                print(f"[Replicas={replicas}|RPS={rps}] Deleting existing NGINX workload if any...", flush=True)
                delete_nginx_workload()
                time.sleep(STABILATION_TIME_AFTER_DELETION)  # Wait for deletion to stabilize

                # Deploy NGINX workload and scale it
                print(f"\n[Replicas={replicas}|RPS={rps}] Deploying NGINX workload...", flush=True)
                deploy_nginx_workload()
                scale_nginx_workload(replicas)

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
                wrk_output_file = run_wrk_test(raw_log_folder, rps)

                # Wait for monitoring threads to finish
                #perf_thread.join()
                #amduprof_thread.join()
                intelpcm_thread.join()
                time.sleep(1)  # Ensure all threads are done before proceeding
                print(f"[Replicas={replicas}|RPS={rps}] Workload traffic completed. File: {wrk_output_file}", flush=True)
                print(f"[Replicas={replicas}|RPS={rps}] PCM monitoring completed.", flush=True)

                print(f"[Replicas={replicas}|RPS={rps}] Parsing and storing workload output...", flush=True)
                workload_metrics = parse_workload_output(wrk_output_file)
                print(f"[Replicas={replicas}|RPS={rps}] Parsed metrics: {workload_metrics}", flush=True)
                
                
                store_workload_metrics(workload_csv, replicas, scenario["name"], workload_metrics, rps, test_id, scenario["id"])

                if scenario["type"]:
                    cleanup_interference(scenario)

                print(f"[Replicas={replicas}|RPS={rps}] Cleanup completed for scenario {scenario['name']}.", flush=True)
                print(f"[Replicas={replicas}|RPS={rps}] Test case {test_id} completed. Waiting for {SLEEP_BETWEEN_TESTS} seconds before next test...", flush=True)

                time.sleep(SLEEP_BETWEEN_TESTS)
                # Clear the raw log folder for the next test
                for file in os.listdir(raw_log_folder):
                    file_path = os.path.join(raw_log_folder, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)

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
                warmup_with_interference(scenario["type"])
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


def main():
    """Main entry point that routes to specific workload testing"""
    if WORKLOAD == "nginx":
        print("Starting NGINX benchmarking", flush=True)
        run_nginx_testing()
    elif WORKLOAD == "redis":
        print("Starting Redis benchmarking")
        run_redis_testing()
    else:
        raise ValueError(f"Unknown workload type: {WORKLOAD}")

if __name__ == "__main__":
    main()