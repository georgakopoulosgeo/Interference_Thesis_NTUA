import csv
import time
from datetime import datetime
from kubernetes import client, config
from kubernetes.utils import create_from_yaml
import yaml
import os

# === Global Config ===
CSV_PATH = "/home/george/Workspace/Interference/interference_injection/ibench_schedule.csv"
TEMPLATE_DIR = "/home/george/Workspace/Interference/interference_injection/ibench_templates"

NAMESPACE = "default"

# === Load Kubernetes Client ===
def load_k8s_client():
    config.load_kube_config()
    return client.ApiClient()

# === Load CSV Schedule ===
def load_schedule():
    with open(CSV_PATH, newline='') as f:
        reader = csv.DictReader(f)
        schedule = [row for row in reader]
        for row in schedule:
            row['timestamp_sec'] = int(row['timestamp_sec'])
            row['duration_sec'] = int(row['duration_sec'])
        return sorted(schedule, key=lambda r: r['timestamp_sec'])

def launch_job(api_client, job_name, template_path, node_selector, duration_sec):
    with open(template_path) as f:
        template = yaml.safe_load(f)

    # Modify the job dynamically
    template['metadata']['name'] = job_name
    template['spec']['template']['metadata']['labels']['app'] = job_name
    container = template['spec']['template']['spec']['containers'][0]
    container['command'][-1] = str(duration_sec)
    template['spec']['template']['spec']['nodeSelector'] = {
        "kubernetes.io/hostname": node_selector
    }

    # Submit the job
    batch_v1 = client.BatchV1Api(api_client)
    batch_v1.create_namespaced_job(namespace=NAMESPACE, body=template)

def delete_job(api_client, job_name):
    batch_v1 = client.BatchV1Api(api_client)
    core_v1 = client.CoreV1Api(api_client)

    # Delete job
    try:
        batch_v1.delete_namespaced_job(
            name=job_name,
            namespace=NAMESPACE,
            body=client.V1DeleteOptions(propagation_policy='Foreground')
        )
    except client.exceptions.ApiException as e:
        print(f"Error deleting job {job_name}: {e}")



def run_scheduler():
    api_client = load_k8s_client()
    schedule = load_schedule()
    start_time = datetime.now()

    for entry in schedule:
        sleep_time = entry['timestamp_sec'] - (datetime.now() - start_time).total_seconds()
        if sleep_time > 0:
            time.sleep(sleep_time)

        job_name = entry['job_name']
        job_type = entry['job_type']
        node_selector = entry['node_selector']
        duration_sec = entry['duration_sec']
        template_path = os.path.join(TEMPLATE_DIR, f"{job_name}.yaml")

        if job_type == "create":
            print(f"[{datetime.now()}] Creating {job_name}")
            launch_job(api_client, job_name, template_path, node_selector, duration_sec)

        elif job_type == "delete":
            print(f"[{datetime.now()}] Deleting {job_name}")
            delete_job(api_client, job_name)

        else:
            print(f"Unknown job_type '{job_type}' in schedule")


if __name__ == "__main__":
    run_scheduler()
