#!/usr/bin/env python3
import subprocess
import csv
import os
import re
import time

def run_workload(script: str, threads: int, connections: int, duration: int, reqs_per_sec: int, wrk2_script_path: str) -> str:
    """
    Run the workload traffic using the specified parameters.
    Returns the raw output of the workload run.
    """
    workload_cmd = [
        script, str(threads), str(connections), str(duration), str(reqs_per_sec), wrk2_script_path
    ]
    result = subprocess.run(workload_cmd, capture_output=True, text=True)
    return result.stdout

def run_workload_single_pod(script, traffic):
    """
    Deploys the nginx workload using a Kubernetes Job via the given shell script.
    'traffic' is one of: light, medium, heavy.
    """
    print(f"Coordinator: Deploying nginx workload job for traffic level '{traffic}'")
    result = subprocess.run([script, traffic], capture_output=True, text=True, check=True)
    return result.stdout

def convert_latency_to_us(latency_str: str) -> float:
    """
    Helper function to convert a latency string to microseconds.
    E.g., "341.52us" -> 341.52, "1.76ms" -> 1760.
    """
    latency_str = latency_str.strip()
    if latency_str.endswith("us"):
        return float(latency_str[:-2])
    elif latency_str.endswith("ms"):
        return float(latency_str[:-2]) * 1000.0
    elif latency_str.endswith("s"):
        return float(latency_str[:-1]) * 1_000_000.0
    else:
        return float(latency_str)

def parse_workload_output(output: str) -> dict:
    """
    Parse the workload generator output to extract throughput and latency metrics.
    Returns a dictionary with keys:
      - throughput: Requests/sec (float)
      - avg_latency: Average latency in microseconds (float)
      - p50_latency, p75_latency, p90_latency, p99_latency, max_latency: latency percentiles (in microseconds)
    """
    metrics = {}
    # Extract throughput from a line like "Requests/sec: 1234.56"
    for line in output.splitlines():
        if "Requests/sec:" in line:
            try:
                throughput = float(line.split(":")[-1].strip())
                metrics["throughput"] = throughput
            except:
                metrics["throughput"] = None
    # Extract average latency from the "Latency" line (ignoring Thread Stats)
    for line in output.splitlines():
        if line.strip().startswith("Latency") and "Thread Stats" not in line:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    metrics["avg_latency"] = convert_latency_to_us(parts[1])
                except:
                    metrics["avg_latency"] = None
            break

    # Extract latency percentiles from lines like "50%   123.45us"
    latency_pattern = re.compile(r"([\d\.]+)%\s+([\d\.]+(us|ms|s))")
    for line in output.splitlines():
        match = latency_pattern.search(line)
        if match:
            percentile = float(match.group(1))
            latency_val = convert_latency_to_us(match.group(2))
            if abs(percentile - 50.0) < 1e-3:
                metrics["p50_latency"] = latency_val
            elif abs(percentile - 75.0) < 1e-3:
                metrics["p75_latency"] = latency_val
            elif abs(percentile - 90.0) < 1e-3:
                metrics["p90_latency"] = latency_val
            elif abs(percentile - 99.0) < 1e-3:
                metrics["p99_latency"] = latency_val
            elif percentile >= 100.0:
                metrics["max_latency"] = latency_val
    return metrics

def parse_workload_output_single_pod() -> dict:
    # Run the command to get the logs of the pod
    # kubectl logs -f job/wrk-load
    cmd = f"kubectl logs -f job/wrk2-load"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    output = result.stdout.strip()
    # Parse the output / use the existing function parse_workload_output
    print("Parsing workload output for single pod", output)
    return parse_workload_output(output)



def store_workload_metrics(csv_file: str, test_case_id: str, date_str: str, interference: str, workload_metrics: dict) -> None:
    """
    Store the workload metrics in a CSV file.
    The CSV includes columns:
      TestCaseID, Interference, Date, Throughput, Avg_Latency, P50_Latency, P75_Latency, P90_Latency, P99_Latency, Max_Latency
    """
    header = [
        "TestCaseID",
        "Interference",
        "Date",
        "Throughput",
        "Avg_Latency",
        "P50_Latency",
        "P75_Latency",
        "P90_Latency",
        "P99_Latency",
        "Max_Latency"
    ]
    file_exists = os.path.exists(csv_file)
    with open(csv_file, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not file_exists:
            writer.writeheader()
        row = {
            "TestCaseID": test_case_id,
            "Interference": interference,
            "Date": date_str,
            "Throughput": workload_metrics.get("throughput", ""),
            "Avg_Latency": workload_metrics.get("avg_latency", ""),
            "P50_Latency": workload_metrics.get("p50_latency", ""),
            "P75_Latency": workload_metrics.get("p75_latency", ""),
            "P90_Latency": workload_metrics.get("p90_latency", ""),
            "P99_Latency": workload_metrics.get("p99_latency", ""),
            "Max_Latency": workload_metrics.get("max_latency", "")
        }
        writer.writerow(row)
