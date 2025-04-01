#!/usr/bin/env python3
import subprocess
import csv
import os
import argparse
import datetime
from data_handling import (
    handle_perf_results,
    handle_amduprof_results,
    parse_workload_output,
    handle_container_metrics_enhanced,
    store_results_in_csv
)

def ensure_directories(script_dir, test_case_id):
    baseline_results_dir = os.path.join(script_dir, "Baseline_Results")
    os.makedirs(baseline_results_dir, exist_ok=True)
    raw_log_folder = os.path.join(baseline_results_dir, f"{test_case_id}_results")
    os.makedirs(raw_log_folder, exist_ok=True)
    return baseline_results_dir, raw_log_folder

def main():
    parser = argparse.ArgumentParser(
        description="Run workload test with extended IO and container metrics monitoring."
    )
    parser.add_argument("test_case_id", help="Test case ID (e.g., TC-IO-01)")
    args = parser.parse_args()
    test_case_id = args.test_case_id

    # Setup directories and file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    baseline_results_dir, raw_log_folder = ensure_directories(script_dir, test_case_id)
    results_csv = os.path.join(baseline_results_dir, "VM_Workload_Results.csv")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    perf_raw_file = os.path.join(raw_log_folder, f"perf_raw_{test_case_id}_{timestamp}.txt")
    amduprof_raw_file = os.path.join(raw_log_folder, f"amduprof_raw_{test_case_id}_{timestamp}.txt")
    container_metrics_file = os.path.join(raw_log_folder, f"container_metrics_{test_case_id}_{timestamp}.csv")

    # Workload parameters and scripts (example values)
    social_network_script = "/home/ubuntu/Workspace/run_social_network.sh"
    wrk2_script_path = "./wrk2/scripts/social-network/compose-post.lua"
    #THREADS = 1
    #CONNECTIONS = 50
    #DURATION = 60  # seconds
    #REQS_PER_SEC = 100
    
    test_cases_csv = os.path.join(script_dir, "VM_Workload_Test_Cases.csv")
    found = False
    with open(test_cases_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["TestCaseID"] == test_case_id:
                THREADS = int(row["THREADS"])
                CONNECTIONS = int(row["CONNECTIONS"])
                DURATION = int(row["DURATION"])
                REQS_PER_SEC = int(row["REQS_PER_SEC"])
                found = True
                break
    if not found:
        print(f"Test case ID {test_case_id} not found in {test_cases_csv}.")
        exit(1)

    # Start perf monitoring
    print("Starting perf monitoring...")
    perf_process = subprocess.Popen([
        "perf", "stat",
        "-e", "cycles,instructions,cache-references,cache-misses,page-faults",
        "--", "sleep", str(DURATION)
    ], stderr=open(perf_raw_file, "w"))

    # Start AMD uProf monitoring
    print("Starting AMD uProf monitoring...")
    amduprof_process = subprocess.Popen([
        "/opt/AMDuProf_5.0-1479/bin/AMDuProfCLI",
        "collect",
        "--system-wide",
        "--duration", str(DURATION),
        "--csv"
    ], stdout=open(amduprof_raw_file, "w"), stderr=subprocess.PIPE)

    # Run the workload
    print("Starting workload...")
    workload_cmd = [
        social_network_script, "workload",
        str(THREADS), str(CONNECTIONS), str(DURATION), str(REQS_PER_SEC), wrk2_script_path
    ]
    workload_result = subprocess.run(workload_cmd, capture_output=True, text=True)
    workload_output = workload_result.stdout

    # Wait for monitoring processes to finish
    perf_process.wait()
    amduprof_process.wait()

    # Parse and aggregate metrics using functions from data_handling.py
    metrics_perf = handle_perf_results(perf_raw_file)
    metrics_amd = handle_amduprof_results(amduprof_raw_file)
    metrics_workload = parse_workload_output(workload_output)
    metrics_container = handle_container_metrics_enhanced(container_metrics_file)
    
    # Print the results
    print("---Perf---", metrics_perf)
    print("---AMD---", metrics_amd)
    print("---Workload---", metrics_workload)
    print("---Container---", metrics_container)

    # Store aggregated results in CSV
    store_results_in_csv(results_csv, test_case_id, date_str,metrics_perf, metrics_amd, metrics_workload, metrics_container)

    print(f"Test Case {test_case_id} completed successfully.")
    print(f"Perf log: {perf_raw_file}")
    print(f"AMDuProf log: {amduprof_raw_file}")
    print(f"Container metrics: {container_metrics_file}")
    print(f"Results stored in: {results_csv}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error occurred: {e}")

