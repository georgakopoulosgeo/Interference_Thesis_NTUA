import csv
import time
from datetime import datetime
from kubernetes import client, config
import yaml
import os
import sys

# === Constants ===
SCHEDULE_FOLDER = "/home/george/Workspace/Interference/interference_injection/interference_schedules"
NAMESPACE = "default"

# YAML file paths for deployments
YAML_DIR = "/home/george/Workspace/Interference/interference_injection/ibench_templates"

# Node selectors by deployment name
NODE_SELECTORS = {
    "ibench-cpu-node1": "minikube",
    "ibench-cpu-node2": "minikube-m02",
    "ibench-l3-node1": "minikube",
    "ibench-l3-node2": "minikube-m02",
    "ibench-membw-node1": "minikube",
    "ibench-membw-node2": "minikube-m02"
}

# === Kubernetes Client ===
def load_k8s_client():
    config.load_kube_config()
    return client.AppsV1Api()

# === Actions ===
def create_deployment(apps_v1, deployment_name, type):
    # Replace the - of the type with _ for the YAML file name
    type = type.replace("-", "_")
    yaml_path = f"{YAML_DIR}/{type}_template.yaml"
    with open(yaml_path) as f:
        dep = yaml.safe_load(f)

    # Override names and labels
    dep['metadata']['name'] = deployment_name
    dep['spec']['selector']['matchLabels']['app'] = deployment_name
    dep['spec']['template']['metadata']['labels']['app'] = deployment_name
    dep['spec']['template']['spec']['containers'][0]['name'] = deployment_name

    # Override node selector based on deployment name
    node_selector_value = NODE_SELECTORS.get(deployment_name)
    if node_selector_value:
        dep['spec']['template']['spec']['nodeSelector'] = {
            "kubernetes.io/hostname": node_selector_value
        }

    apps_v1.create_namespaced_deployment(namespace=NAMESPACE, body=dep)
    print(f"[{datetime.now()}] Created deployment {deployment_name}")

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

def delete_all_deployments(apps_v1):
    for deployment_name in NODE_SELECTORS:
        try:
            apps_v1.delete_namespaced_deployment(
                name=deployment_name,
                namespace=NAMESPACE,
                body=client.V1DeleteOptions(propagation_policy='Foreground')
            )
            print(f"[{datetime.now()}] Deleted deployment {deployment_name}")
        except client.exceptions.ApiException as e:
            if e.status != 404:
                print(f"[{datetime.now()}] ⚠️ Failed to delete {deployment_name}: {e.reason}")


# === Load Schedule ===
def load_schedule(schedule_name):
    path = os.path.join(SCHEDULE_FOLDER, f"{schedule_name}_interference_schedule.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Schedule file not found: {path}")

    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        schedule = []
        for row in reader:
            row['timestamp_sec'] = int(row['timestamp_sec'])
            row['replicas'] = int(row['replicas']) if row['replicas'] else None
            schedule.append(row)
        return sorted(schedule, key=lambda r: r['timestamp_sec'])

# === Main Scheduler ===
def run_scheduler(schedule_name: str, max_minutes: int = None):
    apps_v1 = load_k8s_client()
    schedule = load_schedule(schedule_name)
    start_time = datetime.now()

    for entry in schedule:
        # Stop early if time exceeds limit
        if max_minutes is not None and entry['timestamp_sec'] > max_minutes * 60:
            print(f"[{datetime.now()}] ⏹ Max duration reached ({max_minutes} minutes). Cleaning up...")
            delete_all_deployments(apps_v1)
            break

        # Wait until the appropriate time
        sleep_time = entry['timestamp_sec'] - (datetime.now() - start_time).total_seconds()
        if sleep_time > 0:
            time.sleep(sleep_time)

        action = entry['action']
        deployment_name = entry['deployment_name']
        replicas = entry['replicas']
        dtype = entry['type']

        try:
            if action == 'create':
                create_deployment(apps_v1, deployment_name, dtype)
                if replicas and replicas > 1:
                    scale_deployment(apps_v1, deployment_name, replicas)
            elif action == 'delete':
                delete_deployment(apps_v1, deployment_name)
            else:
                print(f"[{datetime.now()}] Unknown action: {action}")
        except client.exceptions.ApiException as e:
            print(f"[{datetime.now()}] ⚠️ Failed to {action} deployment '{deployment_name}': {e.reason}")
        except Exception as e:
            print(f"[{datetime.now()}] ⚠️ Unexpected error during '{action}' for '{deployment_name}': {e}")



# === Command-line Entry Point ===
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 inject_ibench_pods.py <schedule_name> [duration_minutes]")
        sys.exit(1)

    schedule_name = sys.argv[1]
    max_minutes = int(sys.argv[2]) if len(sys.argv) > 2 else None

    if max_minutes is None:
        print(f"[{datetime.now()}] ▶️ Running full schedule: {schedule_name} (30 min)")
        run_scheduler(schedule_name)
    else:
        print(f"[{datetime.now()}] ▶️ Running schedule '{schedule_name}' for {max_minutes} minutes")
        run_scheduler(schedule_name, max_minutes)
