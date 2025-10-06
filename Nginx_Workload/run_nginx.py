#!/usr/bin/env python3
"""
This script runs the kubectl apply command for a traffic-level-specific YAML file.
Usage:
    python run_kubectl_apply.py [light|medium|heavy]
"""
import subprocess
import sys

def main():
    # Ensure exactly one argument is provided
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} [light|medium|heavy]", file=sys.stderr)
        sys.exit(1)

    traffic = sys.argv[1]
    # Map traffic levels to YAML filenames
    if traffic == "light":
        yaml_file = "wrk-job-light.yaml"
    elif traffic == "medium":
        yaml_file = "wrk-job-medium.yaml"
    elif traffic == "heavy":
        yaml_file = "wrk-job-heavy.yaml"
    else:
        print(f"Invalid traffic level: {traffic}", file=sys.stderr)
        sys.exit(1)

    # Yaml file path
    yaml_file = f"/home/george/Workspace/Interference/workloads/nginx/{yaml_file}"

    # Construct and run the kubectl command
    cmd = ["kubectl", "apply", "-f", yaml_file]
    try:
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error executing '{' '.join(cmd)}': {e.stderr}", file=sys.stderr)
        sys.exit(e.returncode)

if __name__ == "__main__":
    main()
