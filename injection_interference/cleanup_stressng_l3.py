#!/usr/bin/env python3
import subprocess

DEPLOYMENT_NAME = "stress-ng-l3-ways50"

def delete_deployment():
    subprocess.run(
        f"kubectl delete deployment {DEPLOYMENT_NAME} --ignore-not-found",
        shell=True,
        check=True
    )
    print(f"Deleted {DEPLOYMENT_NAME}")

if __name__ == "__main__":
    delete_deployment()