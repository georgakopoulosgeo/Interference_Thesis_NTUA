import csv
import time
from datetime import datetime
from kubernetes import client, config
import yaml

# === Constants ===
CSV_PATH = "/home/george/Workspace/Interference/interference_injection/ibench_schedule.csv"
NAMESPACE = "default"

# YAML file paths for deployments
YAML_PATHS = {
    "ibench-l3-node1": "/home/george/Workspace/Interference/interference_injection/ibench_templates/ibench_l3_node1.yaml",
    "ibench-l3-node2": "/home/george/Workspace/Interference/interference_injection/ibench_templates/ibench_l3_node2.yaml"
}

# === Kubernetes Client ===
def load_k8s_client():
    config.load_kube_config()
    return client.AppsV1Api()

# === Actions ===
def create_deployment(apps_v1, deployment_name):
    yaml_path = YAML_PATHS.get(deployment_name)
    if not yaml_path:
        print(f"[{datetime.now()}] No YAML defined for deployment '{deployment_name}'")
        return

    with open(yaml_path) as f:
        dep = yaml.safe_load(f)
    apps_v1.create_namespaced_deployment(namespace=NAMESPACE, body=dep)
    print(f"[{datetime.now()}] Created {deployment_name}")

def scale_deployment(apps_v1, deployment_name, replicas):
    body = {'spec': {'replicas': replicas}}
    apps_v1.patch_namespaced_deployment_scale(
        name=deployment_name,
        namespace=NAMESPACE,
        body=body
    )
    print(f"[{datetime.now()}] Scaled {deployment_name} to {replicas} replicas")

def delete_deployment(apps_v1, deployment_name):
    apps_v1.delete_namespaced_deployment(
        name=deployment_name,
        namespace=NAMESPACE,
        body=client.V1DeleteOptions(propagation_policy='Foreground')
    )
    print(f"[{datetime.now()}] Deleted {deployment_name}")

# === Load Schedule ===
def load_schedule():
    with open(CSV_PATH, newline='') as f:
        reader = csv.DictReader(f)
        schedule = []
        for row in reader:
            row['timestamp_sec'] = int(row['timestamp_sec'])
            row['replicas'] = int(row['replicas']) if row['replicas'] else None
            schedule.append(row)
        return sorted(schedule, key=lambda r: r['timestamp_sec'])

# === Main Scheduler ===
def run_scheduler():
    apps_v1 = load_k8s_client()
    schedule = load_schedule()
    start_time = datetime.now()

    for entry in schedule:
        # Wait for the correct time
        sleep_time = entry['timestamp_sec'] - (datetime.now() - start_time).total_seconds()
        if sleep_time > 0:
            time.sleep(sleep_time)

        action = entry['action']
        deployment_name = entry['deployment_name']
        replicas = entry['replicas']

        if action == 'create':
            create_deployment(apps_v1, deployment_name)
        elif action == 'scale':
            scale_deployment(apps_v1, deployment_name, replicas)
        elif action == 'delete':
            delete_deployment(apps_v1, deployment_name)
        else:
            print(f"[{datetime.now()}] Unknown action: {action}")

if __name__ == "__main__":
    run_scheduler()
