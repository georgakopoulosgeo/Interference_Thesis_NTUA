#!/usr/bin/env python3
import subprocess
import time
import sys
import os

DEPLOYMENT_NAME = "stress-ng-l3-ways50"
YAML_PATH = "stress-ng/"
YAML_FILE = "stress-ng/stress-ng-l3-50.yaml"
TIMEOUT_SECONDS = 80

def run_command(command):
    """Execute a shell command and return output."""
    try:
        result = subprocess.run(command, shell=True, check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e.stderr}")
        return None

def create_deployment():
    """Create the Kubernetes deployment."""
    print(f"Creating deployment {DEPLOYMENT_NAME} from {YAML_PATH}...")
    output = run_command(f"kubectl apply -f {YAML_FILE}")
    if output:
        print(output.strip())

def scale_deployment(replicas):
    """Scale the deployment to the specified number of replicas."""
    print(f"Scaling deployment to {replicas} replicas...")
    output = run_command(f"kubectl scale deployment {DEPLOYMENT_NAME} --replicas={replicas}")
    if output:
        print(f"Scaled {DEPLOYMENT_NAME} to {replicas} replicas")

def delete_deployment():
    """Delete the Kubernetes deployment."""
    print(f"Deleting deployment {DEPLOYMENT_NAME}...")
    output = run_command(f"kubectl delete deployment {DEPLOYMENT_NAME}")
    if output:
        print(output.strip())

def main():
    # 1. Apply the deployment
    create_deployment()
    
    # 2. Scale if argument provided
    if len(sys.argv) > 1:
        try:
            replicas = int(sys.argv[1])
            if replicas > 0:
                scale_deployment(replicas)
            else:
                print("Replica count must be positive")
        except ValueError:
            print("Invalid argument. Please provide a number for replicas.")
    
    # 3. Wait for the timeout period
    print(f"Waiting {TIMEOUT_SECONDS} seconds for stress-ng to complete...")
    time.sleep(TIMEOUT_SECONDS)
    
    # 4. Delete deployment
    delete_deployment()
    print("Operation completed.")

if __name__ == "__main__":
    main()