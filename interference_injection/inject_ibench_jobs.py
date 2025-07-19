import csv
import time
from datetime import datetime
from kubernetes import client, config
import yaml
import os

# === Configuration ===
CSV_PATH = "/home/george/Workspace/Interference/interference_injection/ibench_schedule.csv"
TEMPLATE_PATH = "/home/george/Workspace/Interference/interference_injection/ibench_templates/ibench_l3.yaml"
NAMESPACE = "default"


# === Load Kubernetes API Client ===
def load_k8s_client():
    config.load_kube_config()
    return client.ApiClient()


# === Load the interference schedule CSV ===
def load_schedule():
    with open(CSV_PATH, newline='') as f:
        reader = csv.DictReader(f)
        schedule = [row for row in reader]
        for row in schedule:
            row['timestamp_sec'] = int(row['timestamp_sec'])
            row['duration_sec'] = int(row['duration_sec'])
        return sorted(schedule, key=lambda r: r['timestamp_sec'])


# === Launch a Job based on the YAML template, dynamically overriding fields ===
def launch_job(api_client, job_name, node_selector, duration_sec):
    with open(TEMPLATE_PATH) as f:
        template = yaml.safe_load(f)

    # Override name and labels
    template['metadata']['name'] = job_name
    template['spec']['template']['metadata']['labels']['app'] = job_name

    # Override command duration
    container = template['spec']['template']['spec']['containers'][0]
    container['command'][-1] = str(duration_sec)

    # Override node selector
    template['spec']['template']['spec']['nodeSelector'] = {
        "kubernetes.io/hostname": node_selector
    }

    # Create the Job in Kubernetes
    batch_v1 = client.BatchV1Api(api_client)
    batch_v1.create_namespaced_job(namespace=NAMESPACE, body=template)


# === Delete a Job and its associated pods ===
def delete_job(api_client, job_name):
    batch_v1 = client.BatchV1Api(api_client)
    try:
        batch_v1.delete_namespaced_job(
            name=job_name,
            namespace=NAMESPACE,
            body=client.V1DeleteOptions(propagation_policy='Foreground')
        )
        print(f"[{datetime.now()}] Deleted job {job_name}")
    except client.exceptions.ApiException as e:
        print(f"[{datetime.now()}] Failed to delete job {job_name}: {e}")


# === Main scheduler loop ===
def run_scheduler():
    api_client = load_k8s_client()
    schedule = load_schedule()
    start_time = datetime.now()

    for entry in schedule:
        # Wait until the correct time for this action
        sleep_time = entry['timestamp_sec'] - (datetime.now() - start_time).total_seconds()
        if sleep_time > 0:
            time.sleep(sleep_time)

        job_name = entry['job_name']
        job_type = entry['job_type']
        node_selector = entry['node_selector']
        duration_sec = entry['duration_sec']

        # Decide action
        if job_type == "create":
            print(f"[{datetime.now()}] Creating job {job_name} on {node_selector} for {duration_sec}s")
            launch_job(api_client, job_name, node_selector, duration_sec)
        elif job_type == "delete":
            print(f"[{datetime.now()}] Deleting job {job_name}")
            delete_job(api_client, job_name)
        else:
            print(f"[{datetime.now()}] Unknown job_type '{job_type}' for job {job_name}")


# === Run the scheduler ===
if __name__ == "__main__":
    run_scheduler()
