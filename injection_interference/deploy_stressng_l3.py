#!/usr/bin/env python3
import time
import argparse
import yaml
from kubernetes import client, config

def main():
    parser = argparse.ArgumentParser(
        description="Deploy stress-ng L3-cache pods, wait 80s, then delete them"
    )
    parser.add_argument(
        'replicas',
        type=int,
        help='Number of L3-stress pods to create'
    )
    parser.add_argument(
        '--namespace',
        type=str,
        default='default',
        help='Kubernetes namespace'
    )
    parser.add_argument(
        '--file',
        type=str,
        default='stress-ng-l3-deploy.yaml',
        help='Path to the stress-ng Deployment YAML'
    )
    args = parser.parse_args()

    # Load kubeconfig and initialize client
    config.load_kube_config()
    api = client.AppsV1Api()
    ns = args.namespace

    # Load and modify the Deployment manifest
    with open(args.file) as f:
        manifest = yaml.safe_load(f)
    manifest['spec']['replicas'] = args.replicas

    # Set the stress-ng command to hammer half of the 8MiB LLC for 80s
    container = manifest['spec']['template']['spec']['containers'][0]
    container['image'] = 'wdhif/stress-ng:latest'
    container['args'] = [
        '--cache', '1',
        '--cache-level', '3',
        '--cache-size', '2M',
        '--timeout', '80s'
    ]

    name = manifest['metadata']['name']

    # Create or scale the Deployment
    try:
        api.create_namespaced_deployment(namespace=ns, body=manifest)
        print(f"Created deployment '{name}' with {args.replicas} replicas.")
    except client.exceptions.ApiException as e:
        if e.status == 409:
            print(f"Deployment '{name}' exists; scaling to {args.replicas} replicas.")
            api.patch_namespaced_deployment_scale(
                name=name, namespace=ns,
                body={'spec': {'replicas': args.replicas}}
            )
        else:
            raise

    # Wait for the stress period
    print("Stressing L3 cache for 80 seconds...")
    time.sleep(80)

    # Tear down
    print(f"Deleting deployment '{name}'...")
    api.delete_namespaced_deployment(
        name=name, namespace=ns,
        body=client.V1DeleteOptions(
            propagation_policy='Foreground',
            grace_period_seconds=0
        )
    )
    print("Deployment deleted.")

if __name__ == '__main__':
    main()
