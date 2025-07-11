import csv
import time
from datetime import datetime
from kubernetes import client, config
from kubernetes.utils import create_from_yaml
import yaml
import os

# === Global Config ===
CSV_PATH = "ibench_schedule.csv"
TEMPLATE_DIR = "ibench_templates"
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

# === Prepare Job Manifest ===
def create_job_yaml(template_path, job_name, duration, node_name):
    with open(template_path, 'r') as f:
        manifest = yaml.safe_load(f)
    
    manifest['metadata']['name'] = job_name
    manifest['spec']['template']['spec']['containers'][0]['command'][1] = str(duration)
    
    # Inject nodeSelector
    manifest['spec']['template']['spec']['nodeSelector'] = {
        'kubernetes.io/hostname': node_name
    }

    return [manifest]


# === Apply Job ===
def submit_job(api_client, manifest):
    create_from_yaml(k8s_client=api_client, yaml_objects=manifest, namespace=NAMESPACE)

# === Main Loop ===
def run_scheduler():
    api_client = load_k8s_client()
    schedule = load_schedule()
    start_time = datetime.now()

    for entry in schedule:
        sleep_time = entry['timestamp_sec'] - (datetime.now() - start_time).total_seconds()
        if sleep_time > 0:
            time.sleep(sleep_time)

        template_file = os.path.join(TEMPLATE_DIR, f"ibench-{entry['job_type']}.yaml")
        manifest = create_job_yaml(
            template_file,
            entry['job_name'],
            entry['duration_sec'],
            entry['node_selector']
        )
        submit_job(api_client, manifest)
        print(f"[{datetime.now()}] Launched {entry['job_name']} ({entry['job_type']})")

if __name__ == "__main__":
    run_scheduler()
