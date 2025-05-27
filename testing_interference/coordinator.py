#!/usr/bin/env python3
"""
NGINX Interference Test Coordinator
- Runs 13 interference scenarios
- Tests with varying replicas (1-5) and RPS (100 to max_RPS)
- Integrates PCM monitoring
- Saves results to CSV files
"""

import os
import time
import csv
import threading
import subprocess
import argparse
import time
from typing import List, Dict, Optional
# Import from other files
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

# Path configuration (add to coordinator.py)
INTERFERENCE_SCRIPTS_DIR = "/home/george/Workspace/Interference/injection_interference"


# Directory setup
RAW_LOG_FOLDER = "raw_logs"
BASELINE_RESULTS_DIR = "results"
os.makedirs(RAW_LOG_FOLDER, exist_ok=True)
os.makedirs(BASELINE_RESULTS_DIR, exist_ok=True)

"""
1. Baseline
2. 1 iBench CPU pod (same node)
3. 2 iBench CPU pods (same node)
4. 4 iBench CPU pods (same node)
5. 8 iBench CPU pods (4 to every node)
6. 1 stress-ng l3 pod 
7. 2 stress-ng l3 pods
8. 4 stress-ng l3 pods
9. 8 stress-ng l3 pods
10. 1 iBench memBW pod 
11. 2 iBench memBW pods
12. 4 iBench memBW pods 
13. 8 iBench memBW pods
and mix scenarios

"""

# Interference scenarios (to be implemented)
INTERFERENCE_SCENARIOS = [
    {"id": 1, "name": "Baseline", "type": None},
    {"id": 2, "name": "1 iBench CPU pod", "type": "ibench-cpu", "count": 1},
    {"id": 3, "name": "2 iBench CPU pods", "type": "ibench-cpu", "count": 2},
    #{"id": 4, "name": "4 iBench CPU pods", "type": "ibench-cpu", "count": 4},
    #{"id": 5, "name": "8 iBench CPU pods", "type": "ibench-cpu", "count": 8},
    {"id": 6, "name": "1 stress-ng l3 pod", "type": "stress-ng-l3", "count": 1},
    {"id": 7, "name": "2 stress-ng l3 pods", "type": "stress-ng-l3", "count": 2},
    #{"id": 8, "name": "4 stress-ng l3 pods", "type": "stress-ng-l3", "count": 4},
    #{"id": 9, "name": "8 stress-ng l3 pods", "type": "stress-ng-l3", "count": 8},
    {"id": 10, "name": "1 iBench memBW pod", "type": "ibench-membw", "count": 1}
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

def cleanup_interference(scenario: Dict):
    """No explicit cleanup needed (pods auto-terminate)"""
    if scenario["type"] is not None:
        print(f"Waiting for {scenario['name']} pods to self-terminate...")
        time.sleep(80)  # Max duration of your interference pods

def cleanup_interference(scenario: Dict):
    """Clean up interference resources"""
    print(f"Cleaning up: {scenario['name']}")
    # TODO: Implement cleanup

def run_wrk_test(replicas: int, rps: int, test_id: str) -> Dict[str, float]:
    """Execute wrk test and return parsed metrics"""
    wrk_output_file = os.path.join(RAW_LOG_FOLDER, f"wrk_output_{test_id}.txt")
    
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

        return {
            "Throughput": float(output.split("Requests/sec:")[1].split()[0]),
            "Avg_Latency": float(output.split("Latency:")[1].split()[0]),
            "P50_Latency": float(output.split("50.000%")[1].split()[0]),
            "P75_Latency": float(output.split("75.000%")[1].split()[0]),
            "P90_Latency": float(output.split("90.000%")[1].split()[0]),
            "P99_Latency": float(output.split("99.000%")[1].split()[0]),
            "Max_Latency": float(output.split("99.999%")[1].split()[0])
        }

    except subprocess.CalledProcessError as e:
        print(f"wrk test failed: {e.stderr}")
        return {k: 0.0 for k in [
            "Throughput", "Avg_Latency", "P50_Latency",
            "P75_Latency", "P90_Latency", "P99_Latency", "Max_Latency"
        ]}

def save_workload_metrics(row: Dict):
    """Append results to workload_metrics.csv"""
    filepath = os.path.join(BASELINE_RESULTS_DIR, "workload_metrics.csv")
    header = [
        "Replicas", "Interference", "Given_RPS", "Throughput",
        "Avg_Latency", "P50_Latency", "P75_Latency", 
        "P90_Latency", "P99_Latency", "Max_Latency"
    ]
    
    write_header = not os.path.exists(filepath)
    
    with open(filepath, "a") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if write_header:
            writer.writeheader()
        writer.writerow(row)



"""
for replicas in REPLICAS_TO_TEST:                   # Outer loop
    for rps in RPS_STEPS:                           # Middle loop
        for scenario in INTERFERENCE_SCENARIOS:     # Inner loop
"""
def test_coordinator():
    """Main test execution loop with proper synchronization"""
    test_case_id = int(time.time())
    
    # Initialize results file
    with open(os.path.join(BASELINE_RESULTS_DIR, "workload_metrics.csv"), "w") as f:
        csv.DictWriter(f, fieldnames=[
            "Replicas", "Interference", "Given_RPS", "Throughput",
            "Avg_Latency", "P50_Latency", "P75_Latency", 
            "P90_Latency", "P99_Latency", "Max_Latency"
        ]).writeheader()

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
                time.sleep(4)  # Stabilization period

                # Generate unique test ID
                test_id = f"{test_case_id}_{scenario['id']}_{replicas}_{rps}"

                pcm_raw_file = os.path.join(RAW_LOG_FOLDER, f"pcm_raw_{test_id}.csv")
                pcm_system_file = os.path.join(BASELINE_RESULTS_DIR, f"pcm_system_{test_id}.csv")
                pcm_core_file = os.path.join(BASELINE_RESULTS_DIR, f"pcm_core_{test_id}.csv")

                # Run test with monitoring
                pcm_thread = threading.Thread(target=pcm_monitoring, args=(46, 5000, pcm_raw_file, pcm_system_file, pcm_core_file))
                
                pcm_thread.start()
                time.sleep(1)
                print(f"[Replicas={replicas}|RPS={rps}] Starting PCM monitoring...")
                #time.sleep(1)  # Give some time for the monitoring to start

                print(f"[Replicas={replicas}|RPS={rps}] Starting workload traffic...")
                # Execute workload test
                metrics = run_wrk_test(replicas, rps, test_id)
                if not metrics:
                    print(f"[Replicas={replicas}|RPS={rps}] Workload test failed, skipping metrics collection.")
                    continue
                print(f"[Replicas={replicas}|RPS={rps}] Workload test completed with metrics: {metrics}")
                # Save results
                with open(os.path.join(BASELINE_RESULTS_DIR, "workload_metrics.csv"), "a") as f:
                    writer = csv.DictWriter(f, fieldnames=[
                        "Replicas", "Interference", "Given_RPS", "Throughput",
                        "Avg_Latency", "P50_Latency", "P75_Latency",
                        "P90_Latency", "P99_Latency", "Max_Latency"
                    ])
                    writer.writerow({
                        "Replicas": replicas,
                        "Interference": scenario["name"],
                        "Given_RPS": rps,
                        **metrics
                    })

                # Wait for PCM monitoring to finish
                pcm_thread.join()
                print(f"[Replicas={replicas}|RPS={rps}] PCM monitoring completed.")
                if scenario["type"]:
                    cleanup_interference(scenario)

                time.sleep(SLEEP_BETWEEN_TESTS)

if __name__ == "__main__":
    test_coordinator()