#!/usr/bin/env python3
import subprocess
import time
import sys

def run_test(yaml_file, duration):
    print(f"Starting test with {yaml_file}...")
    subprocess.run(f"kubectl apply -f {yaml_file}", shell=True, check=True)
    print(f"Running for {duration} seconds...")
    time.sleep(duration)
    subprocess.run(f"kubectl delete -f {yaml_file}", shell=True, check=True)
    print("Test completed")

if __name__ == "__main__":
    test_type = sys.argv[1] if len(sys.argv) > 1 else "50"
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 80

    if test_type == "50":
        run_test("stress-ng/stress-ng-membw-50.yaml", duration)
    elif test_type == "100":
        run_test("stress-ng/stress-ng-membw-100.yaml", duration)
    else:
        print("Usage: ./memory_bandwidth_test.py [50|100] [duration_seconds]")