#!/usr/bin/env python3
import argparse
import time
import yaml
from kubernetes import client, config

# Use: python3 deploy_ibench_membw.py <replicas> [--namespace <namespace>] [--deploy-file <path>] [--duration <seconds>]

def main():
    parser = argparse.ArgumentParser(description="Deploy ibench-membw pods")
    parser.add_argument("replicas", type=int,
                        help="Number of membw replicas to create")
    parser.add_argument("--namespace", default="default",
                        help="Kubernetes namespace")
    parser.add_argument("--deploy-file",
                        default="/home/george/Workspace/Interference/injection_interference/iBench_custom/ibench-membw-deploy.yaml",
                        help="Path to the membw Deployment YAML")
    args = parser.parse_args()

    # Load kubeconfig and initialize API client
    config.load_kube_config()
    apps_v1 = client.AppsV1Api()

    # Read and modify the Deployment manifest
    with open(args.deploy_file) as f:
        dep = yaml.safe_load(f)
    dep['spec']['replicas'] = args.replicas

    name = dep['metadata']['name']
    ns = args.namespace

    # Create or patch the Deployment
    try:
        apps_v1.read_namespaced_deployment(name, ns)
        apps_v1.patch_namespaced_deployment(name, ns, dep)
        print(f"Scaled existing Deployment '{name}' to {args.replicas} replicas in '{ns}'")
    except client.exceptions.ApiException as e:
        if e.status == 404:
            apps_v1.create_namespaced_deployment(namespace=ns, body=dep)
            print(f"Created Deployment '{name}' with {args.replicas} replicas in '{ns}'")
        else:
            raise

if __name__ == "__main__":
    main()
