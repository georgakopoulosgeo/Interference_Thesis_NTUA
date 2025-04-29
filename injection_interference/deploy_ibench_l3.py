import time
import argparse
import yaml
from kubernetes import client, config


def main():
    parser = argparse.ArgumentParser(
        description="Deploy ibench-l3 pods, wait 80s, then delete them"
    )
    parser.add_argument(
        'replicas', type=int,
        help='Number of L3-stress pods to create'
    )
    parser.add_argument(
        '--namespace', default='default',
        help='Kubernetes namespace'
    )
    parser.add_argument(
        '--file', default='/home/george/Workspace/iBench/ibench-l3-deploy.yaml',
        help='Path to the ibench-l3 Deployment YAML'
    )
    args = parser.parse_args()

    # Load kubeconfig
    config.load_kube_config()
    apps = client.AppsV1Api()
    ns = args.namespace

    # Load and modify the Deployment manifest
    with open(args.file) as f:
        manifest = yaml.safe_load(f)
    manifest['spec']['replicas'] = args.replicas

    name = manifest['metadata']['name']

    # Create or update the Deployment
    try:
        apps.create_namespaced_deployment(namespace=ns, body=manifest)
        print(f"Created deployment '{name}' with {args.replicas} replicas.")
    except client.exceptions.ApiException as e:
        if e.status == 409:
            # Already exists: scale it
            print(f"Deployment '{name}' exists, scaling to {args.replicas} replicas.")
            apps.patch_namespaced_deployment_scale(
                name=name, namespace=ns,
                body={'spec': {'replicas': args.replicas}}
            )
        else:
            raise

    # Wait for 80 seconds
    print("Stressing L3 cache for 80 seconds...")
    time.sleep(80)

    # Delete the Deployment
    print(f"Deleting deployment '{name}'...")
    apps.delete_namespaced_deployment(
        name=name,
        namespace=ns,
        body=client.V1DeleteOptions(
            propagation_policy='Foreground',
            grace_period_seconds=0
        )
    )
    print("Deployment deleted.")


if __name__ == '__main__':
    main()