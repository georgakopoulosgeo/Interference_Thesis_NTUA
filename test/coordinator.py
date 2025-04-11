#!/usr/bin/env python3
import os
import csv
import datetime
import argparse
import subprocess
import time

# Import functions from the other modules (assumed to be implemented)
from workload_run_monitor import run_workload, parse_workload_output, store_workload_metrics
from container_monitor import collect_container_metrics
from system_monitor_perf import perf_monitoring
from system_monitor_amduprof import amduprof_monitoring
from system_monitor_intepcm import pcm_monitoring
import threading

# Global configuration
PROMETHEUS_URL = "http://localhost:9090"
STEP = "5"  # 10-second resolution

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
    baseline_results_dir = os.path.join(script_dir, "ResultsV05")
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
    perf_raw_file = os.path.join(raw_log_folder, f"perf_raw_{test_case_id}_{interference}.txt")
    perf_csv = os.path.join(baseline_results_dir, f"perf_metrics_{test_case_id}_{interference}.csv")
    amduprof_raw_file = os.path.join(raw_log_folder, f"amduprof_raw_{test_case_id}_{interference}.txt")
    amduprof_filtered_file = os.path.join(baseline_results_dir, f"amduprof_filtered_{test_case_id}_{interference}.csv")
    pcm_raw_file = os.path.join(raw_log_folder, f"pcm_raw_{test_case_id}_{interference}.csv")
    pcm_system_csv = os.path.join(baseline_results_dir, f"pcm_system_metrics_{test_case_id}_{interference}.csv")
    pcm_core_csv = os.path.join(baseline_results_dir, f"pcm_core_metrics_{test_case_id}_{interference}.csv")
    
    # Define CSV file paths for final aggregated results.
    workload_csv = os.path.join(baseline_results_dir, "workload_metrics.csv")
    system_csv = os.path.join(baseline_results_dir, "system_metrics.csv")
    detail_csv_path = os.path.join(baseline_results_dir, f"container_metrics_detail_{test_case_id}_{interference}.csv")
    agg_csv_path = os.path.join(baseline_results_dir, f"container_metrics_agg_{test_case_id}_{interference}.csv")


    
    # Read workload parameters from the test cases CSV.
    params = read_test_case_parameters(test_cases_csv, test_case_id)
    threads = params["THREADS"]
    connections = params["CONNECTIONS"]
    duration = params["DURATION"]
    reqs_per_sec = params["REQS_PER_SEC"]
    
    # Define workload script paths.
    social_network_script = "/home/george/Workspace/run_social_network.sh"
    wrk2_script_path = "./wrk2/scripts/social-network/compose-post.lua"
    
    print("Coordinator: Starting system-level monitoring...")
    # Run perf_monitoring and amduprof_monitoring in parallel using threads
    perf_thread = threading.Thread(target=perf_monitoring, args=(duration+5, 5000, perf_raw_file, perf_csv))
    #amduprof_thread = threading.Thread(target=amduprof_monitoring, args=(duration+5, 5000, amduprof_raw_file, amduprof_filtered_file))
    intelpcm_thread = threading.Thread(target=pcm_monitoring, args=(duration+5, 5000, pcm_raw_file, pcm_system_csv, pcm_core_csv))

    # ChatGPT comment:
    # Using a thread to run a function that spawns a subprocess is perfectly acceptable.
    # The thread will manage the lifecycle of the subprocess, and the subprocess itself runs as an independent OS process.
    # This setup allows you to run external commands asynchronously, which is often helpful in keeping your main application responsive.

    # Start both threads
    #perf_thread.start()
    #amduprof_thread.start()
    intelpcm_thread.start()
    time.sleep(1)  # Give some time for the monitoring to start
    
    print("Coordinator: Starting workload traffic...")
    start_time_str = str(int(time.time())-10)
    print("Coordinator: Workload Starting time = ", datetime.datetime.now())
    workload_output = run_workload(social_network_script, threads, connections, duration, reqs_per_sec, wrk2_script_path)
    print("Coordinator: Workload Ending time = ", datetime.datetime.now()) # Indeed we are waiting for the workload to finish!
    end_time_str = str(int(time.time()))
    
    print("Coordinator: Starting Container-level monitoring...")
    collect_container_metrics(PROMETHEUS_URL, start_time_str, end_time_str, STEP, test_case_id, interference, date_str, detail_csv_path, agg_csv_path)
    print("Coordinator: Container-level monitoring completed.")

    workload_metrics = parse_workload_output(workload_output)
    
    print("Coordinator: Store workload metrics...")
    store_workload_metrics(workload_csv, test_case_id, date_str, interference, workload_metrics)

    # Wait for monitoring threads to finish
    #perf_thread.join()
    #amduprof_thread.join()
    intelpcm_thread.join()
    
    print(f"Coordinator: Test Case {test_case_id} with Interference {interference} completed.")
    print(f"Coordinator: System logs: {perf_raw_file}, {amduprof_raw_file}, {amduprof_filtered_file}")
    print(f"Coordinator: Results stored in: {workload_csv}, {system_csv}, {detail_csv_path}, {agg_csv_path}")
    print(f"Coordinator: PCM logs: {pcm_raw_file}, {pcm_system_csv}, {pcm_core_csv}")

def main():
    args = parse_arguments()
    test_case_id = args.test_case_id
    interference = args.interference
    # Assuming the test cases CSV is located in the same directory.
    test_cases_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VM_Workload_Test_Cases.csv")
    coordinate_test(test_case_id, interference, test_cases_csv)

if __name__ == "__main__":
    main()
