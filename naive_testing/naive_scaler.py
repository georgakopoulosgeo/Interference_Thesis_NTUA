# naive_scaler.py

import time
import json
import os
from kubernetes import client, config

DEPLOYMENT_NAME = "nginx-naive"
NAMESPACE = "default"
RPS_LOG_PATH = "/home/george/logs/traffic_generator/rps_schedule.jsonl"

RPS_REPLICA_LOOKUP = {
    100: 2, 500: 1, 1000: 2, 1500: 2, 2000: 3,
    2500: 2, 3000: 2, 3500: 2, 4000: 4, 4500: 2,
    5000: 2, 5500: 2, 6000: 2, 6500: 4, 7000: 4
}

def get_latest_rps(filepath):
    try:
        with open(filepath, "r") as f:
            lines = f.readlines()
            if lines:
                last = json.loads(lines[-1])
                return int(last["rps"])
    except Exception as e:
        print(f"[WARN] Failed to read RPS log: {e}")
    return 0

def get_recommended_replicas(rps):
    keys = sorted(RPS_REPLICA_LOOKUP.keys())
    for key in reversed(keys):
        if rps >= key:
            return RPS_REPLICA_LOOKUP[key]
    return 1

def scale_deployment(apps_api, replicas):
    body = {"spec": {"replicas": replicas}}
    apps_api.patch_namespaced_deployment_scale(
        name=DEPLOYMENT_NAME,
        namespace=NAMESPACE,
        body=body
    )

def main():
    config.load_kube_config()
    apps_v1 = client.AppsV1Api()
    last_replicas = -1

    print("Starting Naive RPS-based replica controller...")
    for minute in range(30):  # Run for 30 minutes (adjust if needed)
        rps = get_latest_rps(RPS_LOG_PATH)
        desired = get_recommended_replicas(rps)

        if desired != last_replicas:
            print(f"[Minute {minute+1}] RPS={rps} → scaling to {desired} replicas")
            scale_deployment(apps_v1, desired)
            last_replicas = desired
        else:
            print(f"[Minute {minute+1}] RPS={rps} → no change")

        time.sleep(60)

if __name__ == "__main__":
    main()
