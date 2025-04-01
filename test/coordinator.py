#!/usr/bin/env python3
import os
import csv
import datetime
import argparse
import subprocess

# Import functions from the other modules (assumed to be implemented)
from workload_run_monitor import run_workload, parse_workload_output, store_workload_metrics
from container_monitor import start_container_monitoring, collect_container_metrics, store_container_metrics
from system_monitor import (
    start_perf_monitoring,
    start_amduprof_monitoring,
    wait_for_monitors,
    collect_and_store_system_metrics
)

def parse_arguments():
    # Parse command-line arguments.
    # Expected arguments:
    #   - test_case_id: Identifier for the test case (e.g., TC-IO-01)
    #   - interference: Type of interference (e.g., None, CPU, Memory, etc.)
    parser = argparse.ArgumentParser(description="Coordinator for workload test execution")
    parser.add_argument("test_case_id", help="Test case ID (e.g., TC-IO-01)")
    parser.add_argument("interference", help="Interference type (e.g., None, CPU, Memory)")
    return parser.parse_args()

def ensure_directories(script_dir, test_case_id):
    """
    Create necessary directories for storing results and raw logs.
    Returns the paths to the baseline results directory and the raw log folder.
    """
    baseline_results_dir = os.path.join(script_dir, "ResultsV03")
    os.makedirs(baseline_results_dir, exist_ok=True)
    raw_log_folder = os.path.join(baseline_results_dir, f"{test_case_id}_raw")
    os.makedirs(raw_log_folder, exist_ok=True)
    return baseline_results_dir, raw_log_folder

def read_test_case_parameters(test_cases_csv, test_case_id):
    """
    Reads the test case parameters from the CSV file.
    Returns a dictionary with keys: THREADS, CONNECTIONS, DURATION, REQS_PER_SEC.
    """
    with open(test_cases_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["TestCaseID"] == test_case_id:
                return {
                    "THREADS": int(row["THREADS"]),
                    "CONNECTIONS": int(row["CONNECTIONS"]),
                    "DURATION": int(row["DURATION"]),
                    "REQS_PER_SEC": int(row["REQS_PER_SEC"])
                }
    raise ValueError(f"Test case ID {test_case_id} not found in {test_cases_csv}")

def coordinate_test(test_case_id, interference, test_cases_csv):
    """
    Coordinates the overall test:
      1. Sets up directories and file paths.
      2. Reads workload parameters from the test cases CSV.
      3. Starts system-level and container-level monitoring.
      4. Starts the workload traffic.
      5. Waits for traffic completion.
      6. Stops monitoring, collects metrics, and stores results.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    baseline_results_dir, raw_log_folder = ensure_directories(script_dir, test_case_id)
    
    # Create timestamp and date strings for file naming and logging.
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Define file paths for raw monitoring logs.
    perf_raw_file = os.path.join(raw_log_folder, f"perf_raw_{test_case_id}_{timestamp}.txt")
    amduprof_raw_file = os.path.join(raw_log_folder, f"amduprof_raw_{test_case_id}_{timestamp}.txt")
    container_metrics_file = os.path.join(raw_log_folder, f"container_metrics_{test_case_id}_{timestamp}.csv")
    
    # Define CSV file paths for final aggregated results.
    workload_csv = os.path.join(baseline_results_dir, "workload_metrics.csv")
    container_csv = os.path.join(baseline_results_dir, "container_metrics.csv")
    system_csv = os.path.join(baseline_results_dir, "system_metrics.csv")
    
    # Read workload parameters from the test cases CSV.
    params = read_test_case_parameters(test_cases_csv, test_case_id)
    threads = params["THREADS"]
    connections = params["CONNECTIONS"]
    duration = params["DURATION"]
    reqs_per_sec = params["REQS_PER_SEC"]
    
    # Define workload script paths.
    social_network_script = "/home/ubuntu/Workspace/run_social_network.sh"
    wrk2_script_path = "./wrk2/scripts/social-network/compose-post.lua"
    
    print("Starting system-level monitoring...")
    # Start perf and AMD uProf monitoring.
    perf_process = start_perf_monitoring(duration, perf_raw_file)
    amduprof_process = start_amduprof_monitoring(duration, amduprof_raw_file)
    
    print("Starting container-level monitoring...")
    # Start container monitoring.
    container_monitor_process = start_container_monitoring(container_metrics_file)
    
    print("Starting workload traffic...")
    # Run the workload and capture its output.
    workload_output = run_workload(social_network_script, threads, connections, duration, reqs_per_sec, wrk2_script_path)
    
    print("Waiting for workload to complete...")
    # If run_workload is asynchronous, you could wait here; 
    # assuming it runs synchronously and returns when done.
    
    print("Stopping system-level monitoring...")
    # Wait for the system monitoring processes to complete.
    wait_for_monitors(perf_process, amduprof_process)
    
    print("Stopping container-level monitoring...")
    # Terminate the container monitoring process.
    container_monitor_process.terminate()
    container_monitor_process.wait()
    
    print("Collecting and processing metrics...")
    # Process workload metrics.
    workload_metrics = parse_workload_output(workload_output)
    # Let system_monitor module automatically handle system metrics storage.
    collect_and_store_system_metrics(perf_raw_file, amduprof_raw_file, system_csv, test_case_id, date_str, interference)
    # Process container metrics.
    container_metrics = collect_container_metrics(container_metrics_file)
    
    print("Storing metrics to CSV files...")
    store_workload_metrics(workload_csv, test_case_id, date_str, interference, workload_metrics)
    #store_system_metrics(system_csv, test_case_id, date_str, interference ,system_metrics)
    store_container_metrics(container_csv, test_case_id, date_str, container_metrics)
    
    print(f"Test Case {test_case_id} with Interference {interference} completed.")
    print(f"System logs: {perf_raw_file}, {amduprof_raw_file}")
    print(f"Container metrics log: {container_metrics_file}")
    print(f"Results stored in: {workload_csv}, {system_csv}, {container_csv}")

def main():
    args = parse_arguments()
    test_case_id = args.test_case_id
    interference = args.interference
    # Assuming the test cases CSV is located in the same directory.
    test_cases_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VM_Workload_Test_Cases.csv")
    coordinate_test(test_case_id, interference, test_cases_csv)

if __name__ == "__main__":
    main()
