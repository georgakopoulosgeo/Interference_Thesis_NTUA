# naive_scaler.py

import time
import json
import os
from kubernetes import client, config
import logging
from arima import predict_next_rps, train_arima_model

logging.basicConfig(level=logging.INFO) # Logging setup
last_applied_plan = None

DEPLOYMENT_NAME = "nginx-naive"
NAMESPACE = "default"
RPS_LOG_PATH = "/home/george/logs/traffic_generator/rps_schedule.jsonl"
CHECK_INTERVAL_SEC = 60  # Check every minute


def get_latest_rps(filepath):
    try:
        with open(filepath, "r") as f:
            lines = f.readlines()
            if lines:
                last = json.loads(lines[-1])
                # If the last entry is less than 25 seconds before, wait for 25 seconds:
                
                return int(last["rps"])
    except Exception as e:
        print(f"[WARN] Failed to read RPS log: {e}")
    return 0

# Get the number of replicas needed based on forecasted RPS from the replica_lookup.json file
def determine_replica_count_for_rps(predicted_rps: int) -> int:
    try:
        with open("replica_lookup.json", "r") as f:
            lookup_table = json.load(f)

        # Sort by rps 
        sorted_table = sorted(lookup_table, key=lambda x: x["RPS"])

        recommended = None
        for entry in sorted_table:
            if entry["RPS"] <= predicted_rps:
                recommended = entry["Recommended_Replicas"]
            else:
                break

        if recommended is not None:
            return recommended
        else:
            # Fallback: return minimum available recommendation
            return sorted_table[0]["Recommended_Replicas"]

    except Exception as e:
        print(f"❌ Failed to determine replica count: {e}")
        return 1  # Safe fallback   

def scale_deployment(apps_api, replicas):
    body = {"spec": {"replicas": replicas}}
    apps_api.patch_namespaced_deployment_scale(
        name=DEPLOYMENT_NAME,
        namespace=NAMESPACE,
        body=body
    )

def naive_loop():
    config.load_kube_config()
    apps_v1 = client.AppsV1Api()
    last_replicas = -1

    logging.info("Starting Naive RPS-based replica controller...")
    while True:
        start_time = time.time()
        logging.info("Controller loop triggered.")

        # 1. Ensure model is trained before predictions
        train_arima_model()  

        # 2. Get latest RPS from the log file
        forecasted_rps = predict_next_rps()
        replicas_needed = determine_replica_count_for_rps(rps)

        if replicas_needed != last_replicas:
            scale_deployment(apps_v1, replicas_needed)
            last_replicas = replicas_needed

        elapsed = time.time() - start_time
        time.sleep(max(0, CHECK_INTERVAL_SEC - elapsed))

if __name__ == "__main__":
    naive_loop()
