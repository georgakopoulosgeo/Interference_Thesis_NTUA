#!/usr/bin/env python3
"""
NGINX Load Test Script (wrk2 + Vegeta)
- Runs wrk2 tests first, then Vegeta tests
- Stores results in separate CSV files
- Maintains identical test parameters for both tools
"""

import subprocess
import time
import csv
import json
import os
from typing import List, Tuple, Dict, Any

# Configuration
SERVICE_URL = "http://192.168.49.2:30080"
WRK_PATH = "/home/george/Workspace/Interference/workloads/wrk2/wrk"
VEGETA_PATH = "vegeta"  # Ensure vegeta is in PATH
MIN_REPLICAS = 1
MAX_REPLICAS = 5
REQUEST_RATES = [100, 200, 300, 400, 500, 600, 700, 800, 1000, 1200]
DURATION = "40s"
CONCURRENT_CONNS = 40
THREADS = 1
SLEEP_BETWEEN_TESTS = 10

# Results files
WRK_RESULTS_FILE = "wrk_results.csv"
VEGETA_RESULTS_FILE = "vegeta_results.csv"

def run_kubectl(*args) -> Tuple[bool, str]:
    """Execute kubectl command with error handling"""
    try:
        result = subprocess.run(
            ["kubectl"] + list(args),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def parse_latency(latency_str: str) -> float:
    """Convert wrk2 latency string (us/ms) to milliseconds"""
    if "us" in latency_str:
        return float(latency_str.replace("us", "")) / 1000
    elif "ms" in latency_str:
        return float(latency_str.replace("ms", ""))
    return 0.0

# ------------------------- wrk2 Functions -------------------------
def run_wrk(rate: int) -> Tuple[float, float, float, float, int]:
    """Execute wrk test and parse metrics"""
    cmd = [
        WRK_PATH,
        f"-t{THREADS}",
        f"-c{CONCURRENT_CONNS}",
        f"-d{DURATION}",
        f"-R{rate}",
        "-L",
        SERVICE_URL
    ]
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        output = result.stdout

        req_sec = float(output.split("Requests/sec:")[1].split()[0])
        p90 = parse_latency(output.split("90.000%")[1].split()[0])
        p99 = parse_latency(output.split("99.000%")[1].split()[0])
        p99999 = parse_latency(output.split("99.999%")[1].split()[0])
        errors = int(output.split("Non-2xx responses:")[1].split()[0]) if "Non-2xx" in output else 0

        return req_sec, p90, p99, p99999, errors
    except Exception as e:
        print(f"wrk error: {str(e)}")
        return 0.0, 0.0, 0.0, 0.0, 0

def wrk_test_combination(replicas: int, rate: int) -> List[str]:
    """Test one replica/rate combination with wrk"""
    print(f"\n[wrk] Testing {replicas} replicas at {rate} req/sec")
    
    # Scale deployment
    success, output = run_kubectl("scale", "deployment", "my-nginx", f"--replicas={replicas}")
    if not success:
        print(f"Scaling failed: {output}")
        return [str(replicas), str(rate), "SCALE_FAILED", "N/A", "N/A", "N/A", "N/A"]
    
    time.sleep(8)  # Wait for stabilization
    
    # Run test
    req_sec, p90, p99, p99999, errors = run_wrk(rate)
    print(f"Results: {req_sec:.1f} req/sec | P90: {p90:.2f}ms | P99: {p99:.2f}ms | P99.999: {p99999:.2f}ms | Errors: {errors}")
    
    return [str(replicas), str(rate), f"{req_sec:.1f}", f"{p90:.2f}", f"{p99:.2f}", f"{p99999:.2f}", str(errors)]

# ------------------------- Vegeta Functions -------------------------
def run_vegeta(rate: int) -> Dict[str, Any]:
    """Execute Vegeta test and return parsed results"""
    targets_path = "vegeta_targets.txt"
    results_path = "vegeta_results.bin"
    
    with open(targets_path, "w") as f:
        f.write(f"GET {SERVICE_URL}")
    
    try:
        subprocess.run(
            [
                VEGETA_PATH, "attack",
                "-rate", str(rate),
                "-duration", DURATION,
                "-targets", targets_path,
                "-output", results_path
            ],
            check=True
        )
        
        report = subprocess.run(
            [VEGETA_PATH, "report", "-type=json", results_path],
            stdout=subprocess.PIPE,
            check=True
        )
        return json.loads(report.stdout.decode())
    finally:
        for f in [targets_path, results_path]:
            if os.path.exists(f):
                os.remove(f)

def vegeta_test_combination(replicas: int, rate: int) -> List[str]:
    """Test one replica/rate combination with Vegeta"""
    print(f"\n[Vegeta] Testing {replicas} replicas at {rate} req/sec")
    
    # Scale deployment (same as wrk)
    success, output = run_kubectl("scale", "deployment", "my-nginx", f"--replicas={replicas}")
    if not success:
        print(f"Scaling failed: {output}")
        return [str(replicas), str(rate), "SCALE_FAILED", "N/A", "N/A", "N/A", "N/A"]
    
    time.sleep(8)
    
    # Run test
    results = run_vegeta(rate)
    req_sec = results["rate"]
    p90 = results["latencies"]["90th"] / 1e6  # ns → ms
    p99 = results["latencies"]["99th"] / 1e6
    p99999 = results["latencies"]["max"] / 1e6
    errors = results["errors"]
    
    print(f"Results: {req_sec:.1f} req/sec | P90: {p90:.2f}ms | P99: {p99:.2f}ms | P99.999: {p99999:.2f}ms | Errors: {errors}")
    
    return [str(replicas), str(rate), f"{req_sec:.1f}", f"{p90:.2f}", f"{p99:.2f}", f"{p99999:.2f}", str(errors)]

# ------------------------- Main Execution -------------------------
def main():
    # Verify tools are available
    for tool, path in [("wrk", WRK_PATH), ("vegeta", VEGETA_PATH)]:
        if not os.path.exists(path):
            print(f"Error: {tool} not found at {path}")
            return

    # Verify cluster access
    success, _ = run_kubectl("get", "nodes")
    if not success:
        print("Error: Could not connect to Kubernetes cluster")
        return

    # ------------------------- wrk2 Tests -------------------------
    print("\n" + "="*50)
    print("Starting wrk2 Tests")
    print("="*50)
    
    with open(WRK_RESULTS_FILE, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["Replicas", "Request Rate", "Actual Req/Sec", "P90 Latency (ms)", "P99 Latency (ms)", "P99.999 Latency (ms)", "Errors"])
    
    for replicas in range(MIN_REPLICAS, MAX_REPLICAS + 1):
        for rate in REQUEST_RATES:
            row = wrk_test_combination(replicas, rate)
            with open(WRK_RESULTS_FILE, "a") as f:
                csv.writer(f).writerow(row)
            time.sleep(SLEEP_BETWEEN_TESTS)

    # ------------------------- Vegeta Tests -------------------------
    print("\n" + "="*50)
    print("Starting Vegeta Tests")
    print("="*50)
    
    with open(VEGETA_RESULTS_FILE, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["Replicas", "Request Rate", "Actual Req/Sec", "P90 Latency (ms)", "P99 Latency (ms)", "P99.999 Latency (ms)", "Errors"])
    
    for replicas in range(MIN_REPLICAS, MAX_REPLICAS + 1):
        for rate in REQUEST_RATES:
            row = vegeta_test_combination(replicas, rate)
            with open(VEGETA_RESULTS_FILE, "a") as f:
                csv.writer(f).writerow(row)
            time.sleep(SLEEP_BETWEEN_TESTS)

    print("\nTests completed:")
    print(f"- wrk2 results: {WRK_RESULTS_FILE}")
    print(f"- Vegeta results: {VEGETA_RESULTS_FILE}")

if __name__ == "__main__":
    main()