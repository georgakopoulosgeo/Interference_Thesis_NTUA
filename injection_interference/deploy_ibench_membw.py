import time
import argparse
import yaml
from kubernetes import client, config

## Use: python3 deploy_ibench_membw.py <replicas> [--namespace <namespace>] [--nginx]

def main():
    parser = argparse.ArgumentParser(
        description="Deploy ibench pods with optional Nginx node targeting"
    )
    parser.add_argument(
        'replicas', type=int,
        help='Number of ibench pods to create'
    )
    parser.add_argument(
        '--namespace', default='default',
        help='Kubernetes namespace'
    )
    parser.add_argument(
        '--nginx', action='store_true',
        help='Deploy to node with nginx=true label'
    )
    args = parser.parse_args()

    # Load kubeconfig
    config.load_kube_config()
    apps = client.AppsV1Api()
    ns = args.namespace

    # Select the appropriate YAML file
    yaml_file = '/home/george/Workspace/Interference/injection_interference/iBench_custom/ibench-nginx-node-membw.yaml' if args.nginx else './iBench_custom/ibench-regular-node-membw.yaml'

    # Load and modify the Deployment manifest
    with open(yaml_file) as f:
        manifest = yaml.safe_load(f)
    manifest['spec']['replicas'] = args.replicas

    name = manifest['metadata']['name']

    # Create or update the Deployment
    try:
        apps.create_namespaced_deployment(namespace=ns, body=manifest)
        print(f"Created deployment '{name}' with {args.replicas} replicas on {'Nginx node' if args.nginx else 'any node'}.")
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

if __name__ == '__main__':
    main()