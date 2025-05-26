#!/usr/bin/env python3
"""
NGINX Load Test Script
- Scales NGINX replicas systematically
- Tests with increasing request rates
- Captures P99 latency and throughput
- Tesing is taskset -c 6,7 ./wrk -t1 -c40 -d30s -R100 -L http://192.168.49.2:30080/

Run with:
taskset -c 6,7 python3 nginx-testing-rps-replicas.py
"""

import subprocess
import time
import csv
from typing import List, Tuple

# Configuration
SERVICE_URL = "http://192.168.49.2:30080"
WRK_PATH = "/home/george/Workspace/Interference/workloads/wrk2/wrk"
MIN_REPLICAS = 1
MAX_REPLICAS = 5
REQUEST_RATES = [100, 200, 300, 400, 500, 600, 700, 800, 1000, 1200]
DURATION = "40s"
CONCURRENT_CONNS = 40
THREADS = 1
SLEEP_BETWEEN_TESTS = 10
RESULTS_FILE = "load_test_results.csv"

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
        return float(latency_str.replace("us", "")) / 1000  # Convert µs to ms
    elif "ms" in latency_str:
        return float(latency_str.replace("ms", ""))
    else:
        return 0.0  # Fallback

def run_wrk(rate: int) -> Tuple[float, float, float, int]:
    """Execute wrk test with proper latency parsing"""
    print(f"Running wrk...")
    try:
        result = subprocess.run(
            [WRK_PATH, f"-t{THREADS}", f"-c{CONCURRENT_CONNS}", 
             f"-d{DURATION}", f"-R{rate}", "-L", SERVICE_URL],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        output = result.stdout

        # Parse metrics
        req_sec = float(output.split("Requests/sec:")[1].split()[0])
        p90_str = output.split("90.000%")[1].split()[0]  # Raw string
        p90_latency = parse_latency(p90_str)
        p99_str = output.split("99.000%")[1].split()[0]  # Raw string (e.g., "454.00us")
        p99_latency = parse_latency(p99_str)
        p99_999_str = output.split("99.999%")[1].split()[0]  # Raw string (e.g., "454.00us")
        p99_999_latency = parse_latency(p99_999_str)
        errors = int(output.split("Non-2xx responses:")[1].split()[0]) if "Non-2xx" in output else 0

        return req_sec, p99_latency, p90_latency, p99_999_latency, errors

    except Exception as e:
        print(f"WRK error: {str(e)}")
        return 0.0, 0.0, 0

def test_combination(replicas: int, rate: int) -> List[str]:
    """Test one replica/rate combination"""
    print(f"\n--- Testing {replicas} replicas at {rate} req/sec ---")
    
    # Scale deployment
    success, output = run_kubectl("scale", "deployment","my-nginx", f"--replicas={replicas}")
    if not success:
        print(f"Scaling failed: {output}")
        return [str(replicas), str(rate), "SCALE_FAILED", "N/A", "N/A"]
    print(f"Scaled to  {replicas} replicas / Waiting for Stabilization")
    time.sleep(8)  # Wait for stabilization
    
    # Run test
    req_sec, p99, p90, p99_999, errors = run_wrk(rate)
    print(f"Results: {req_sec:.1f} req/sec | P90: {p90} ms | P99: {p99} ms | P99.999: {p99_999} ms | Errors: {errors}")
    
    return [str(replicas), str(rate), f"{req_sec:.1f}", f"{p90}", f"{p99}", f"{p99_999}", str(errors)]

def main():
    # Verify cluster access
    success, _ = run_kubectl("get", "nodes")
    if not success:
        print("Error: Could not connect to Kubernetes cluster. Is minikube running?")
        print("Try: minikube start")
        return
    
    # Prepare results file
    with open(RESULTS_FILE, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["Replicas", "Request Rate", "Actual Req/Sec", "P90 Latency (ms)", "P99 Latency (ms)", "P99.999 Latency (ms)", "Errors"])
    
    # Run all test combinations
    for replicas in range(MIN_REPLICAS, MAX_REPLICAS + 1):
        for rate in REQUEST_RATES:
            row = test_combination(replicas, rate)
            
            # Save results
            with open(RESULTS_FILE, "a") as f:
                writer = csv.writer(f)
                writer.writerow(row)
            
            time.sleep(SLEEP_BETWEEN_TESTS)
    
    print(f"\nTest complete. Results saved to {RESULTS_FILE}")

if __name__ == "__main__":
    main()
