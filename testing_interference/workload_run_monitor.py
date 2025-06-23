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

def run_workload_single_pod(script):
    """
    Deploys the nginx workload using a Kubernetes Job via the given shell script.
    'traffic' is one of: light, medium, heavy.
    """
    #print(f"Coordinator: Deploying nginx workload job for traffic level '{traffic}'")
    #result = subprocess.run([script, traffic], capture_output=True, text=True, check=True)
    #return result.stdout
    return

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

def parse_workload_output(wrk_output_file: str) -> dict:
    """
    Parse the workload generator output file to extract throughput and latency metrics.
    Returns a dictionary with keys:
      - throughput: Requests/sec (float)
      - avg_latency: Average latency in microseconds (float)
      - p50_latency, p75_latency, p90_latency, p99_latency, max_latency: latency percentiles (in microseconds)
    """
    metrics = {}
    
    # Read the content from the file
    try:
        with open(wrk_output_file, 'r') as f:
            output = f.read()
    except IOError:
        raise ValueError(f"Could not read file: {wrk_output_file}")

    # Extract throughput from a line like "Requests/sec: 1234.56"
    for line in output.splitlines():
        if "Requests/sec:" in line:
            try:
                throughput = float(line.split(":")[-1].strip())
                metrics["throughput"] = throughput
            except:
                metrics["throughput"] = None
                break  # No need to keep looking if we found the line
    
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



def store_workload_metrics(csv_file: str, replicas: int, interference: str, workload_metrics: dict, given_rps: int, test_id: str) -> None:
    """
    Store the workload metrics in a CSV file.
    The CSV includes columns:
      TestCaseID, Interference, Date, Throughput, Avg_Latency, P50_Latency, P75_Latency, P90_Latency, P99_Latency, Max_Latency
    """
    header = [
        "Test_ID",
        "Replicas",
        "Interference",
        "Given_RPS",
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
            "Test_ID": test_id,
            "Replicas": replicas,
            "Interference": interference,
            "Given_RPS": given_rps,
            "Throughput": workload_metrics.get("throughput", ""),
            "Avg_Latency": workload_metrics.get("avg_latency", ""),
            "P50_Latency": workload_metrics.get("p50_latency", ""),
            "P75_Latency": workload_metrics.get("p75_latency", ""),
            "P90_Latency": workload_metrics.get("p90_latency", ""),
            "P99_Latency": workload_metrics.get("p99_latency", ""),
            "Max_Latency": workload_metrics.get("max_latency", "")
        }
        writer.writerow(row)


################ REDIS METRICS PARSING AND STORAGE ################

def parse_memtier_output(memtier_output_file: str) -> dict:
    """
    Parse the memtier_benchmark output file to extract throughput and latency metrics.
    Returns a dictionary with keys:
      - throughput: Ops/sec (float)
      - avg_latency: Average latency in milliseconds (float)
      - p50_latency, p90_latency, p99_latency, p99.9_latency: latency percentiles (in milliseconds)
      - sets_ops: Sets operations per second
      - gets_ops: Gets operations per second
    """
    metrics = {
        'throughput': 0.0,
        'avg_latency': 0.0,
        'p50_latency': 0.0,
        'p90_latency': 0.0,
        'p99_latency': 0.0,
        'p99.9_latency': 0.0,
        'sets_ops': 0.0,
        'gets_ops': 0.0
    }

    try:
        with open(memtier_output_file, 'r') as f:
            output = f.read()
    except IOError:
        raise ValueError(f"Could not read file: {memtier_output_file}")

    # Extract total throughput from the "Totals" line
    totals_pattern = re.compile(
        r"Totals\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)"
    )
    
    # Extract SETS and GETS specific metrics
    sets_pattern = re.compile(
        r"Sets\s+([\d\.]+)\s+---\s+---\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)"
    )
    gets_pattern = re.compile(
        r"Gets\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)"
    )

    for line in output.splitlines():
        if "Totals" in line:
            match = totals_pattern.search(line)
            if match:
                metrics['throughput'] = float(match.group(1))
                metrics['avg_latency'] = float(match.group(4))
                metrics['p50_latency'] = float(match.group(5))
                metrics['p90_latency'] = float(match.group(6))
                metrics['p99_latency'] = float(match.group(7))
                metrics['p99.9_latency'] = float(match.group(8))
        
        elif "Sets" in line:
            match = sets_pattern.search(line)
            if match:
                metrics['sets_ops'] = float(match.group(1))
                
        elif "Gets" in line:
            match = gets_pattern.search(line)
            if match:
                metrics['gets_ops'] = float(match.group(1))

    return metrics


def store_redis_metrics(csv_file: str, replicas: int, interference: str, scenario: str, 
                       redis_metrics: dict, clients: int, test_id: str) -> None:
    """
    Store the Redis metrics in a CSV file.
    The CSV includes columns:
      Test_ID, Replicas, Interference, Scenario, Throughput, Avg_Latency, 
      P50_Latency, P90_Latency, P99_Latency, P99.9_Latency, Clients,
      Sets_Ops, Gets_Ops
    """
    header = [
        "Test_ID",
        "Replicas",
        "Interference",
        "Scenario",
        "Throughput",
        "Avg_Latency",
        "P50_Latency",
        "P90_Latency",
        "P99_Latency",
        "P99.9_Latency",
        "Clients",
        "Sets_Ops",
        "Gets_Ops"
    ]
    
    file_exists = os.path.exists(csv_file)
    with open(csv_file, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not file_exists:
            writer.writeheader()
        row = {
            "Test_ID": test_id,
            "Replicas": replicas,
            "Interference": interference,
            "Scenario": scenario,
            "Throughput": redis_metrics.get("throughput", 0),
            "Avg_Latency": redis_metrics.get("avg_latency", 0),
            "P50_Latency": redis_metrics.get("p50_latency", 0),
            "P90_Latency": redis_metrics.get("p90_latency", 0),
            "P99_Latency": redis_metrics.get("p99_latency", 0),
            "P99.9_Latency": redis_metrics.get("p99.9_latency", 0),
            "Clients": clients,
            "Sets_Ops": redis_metrics.get("sets_ops", 0),
            "Gets_Ops": redis_metrics.get("gets_ops", 0)
        }
        writer.writerow(row)