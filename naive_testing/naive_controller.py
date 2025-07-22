# naive_scaler.py

import time
import json
import os
from kubernetes import client, config
import logging
import sys
from datetime import datetime, timezone
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

def get_actual_replicas_per_node(label_selector="app=nginx-naive"):
    """
    Returns a dictionary like: {'minikube': 2, 'minikube-m02': 1}
    Counts how many running pods (Ready=True) exist per node for the given label.
    """
    core_v1 = client.CoreV1Api()
    node_replica_count = {}

    pods = core_v1.list_namespaced_pod(namespace=NAMESPACE, label_selector=label_selector).items
    for pod in pods:
        if pod.status.phase != "Running":
            continue

        conditions = {cond.type: cond.status for cond in pod.status.conditions or []}
        if conditions.get("Ready") != "True":
            continue

        node_name = pod.spec.node_name
        node_replica_count[node_name] = node_replica_count.get(node_name, 0) + 1

    return node_replica_count


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

def log_naive_plan(log_path, rps, replicas, actual_distribution):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rps": rps,
        "desired_replicas": replicas,
        "replica_distribution": actual_distribution
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def naive_loop(log_path):
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
        logging.info(f"Forecasted RPS: {forecasted_rps}")

        # 3. Determine the number of replicas needed based on forecasted RPS  
        replicas_needed = determine_replica_count_for_rps(forecasted_rps)
        logging.info(f"Determined replicas needed: {replicas_needed}")

        if replicas_needed != last_replicas:
            scale_deployment(apps_v1, replicas_needed)
            last_replicas = replicas_needed
            logging.info(f"Scaled deployment to {replicas_needed} replicas.")
            # Wait a few seconds for pods to stabilize
            logging.info("Waiting 5 seconds for replicas to stabilize...")
            time.sleep(5)

        # After stabilization, get actual distribution
        actual_replicas = get_actual_replicas_per_node()
        logging.info(f"Replica distribution: {actual_replicas}")
        log_naive_plan(log_path, forecasted_rps, replicas_needed, actual_replicas)

        elapsed = time.time() - start_time
        time.sleep(max(0, CHECK_INTERVAL_SEC - elapsed))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 naive_controller.py <interference_filename>")
        print("Example: python3 naive_controller.py cpu_naive_v03")
        sys.exit(1)

    log_filename = sys.argv[1]
    log_path = os.path.join("/home/george/logs/naive", log_filename)
    os.makedirs("/home/george/logs/naive", exist_ok=True)
    if not log_path.endswith(".jsonl"):
        log_path += ".jsonl"

    naive_loop(log_path)
