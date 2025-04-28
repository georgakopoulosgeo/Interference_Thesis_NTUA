import time
import argparse
from kubernetes import client, config


def main():
    parser = argparse.ArgumentParser(description="Deploy ibench-cpu, scale replicas, then destroy after delay.")
    parser.add_argument(
        'replicas',
        type=int,
        help='Number of replicas to scale the ibench-cpu deployment to.'
    )
    parser.add_argument(
        '--namespace',
        type=str,
        default='default',
        help='Kubernetes namespace to deploy into.'
    )
    parser.add_argument(
        '--delay',
        type=int,
        default=90,
        help='Time in seconds to wait before destroying the deployment.'
    )
    args = parser.parse_args()

    # Load kubeconfig and initialize API client
    config.load_kube_config()
    apps_v1 = client.AppsV1Api()

    # Define the initial deployment manifest
    deployment = client.V1Deployment(
        api_version='apps/v1',
        kind='Deployment',
        metadata=client.V1ObjectMeta(name='ibench-cpu'),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(
                match_labels={'app': 'ibench-cpu'}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={'app': 'ibench-cpu'}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name='ibench',
                            image='ibench:latest',
                            image_pull_policy='IfNotPresent',
                            command=['./cpu', '80'],
                            resources=client.V1ResourceRequirements(
                                requests={'cpu': '1', 'memory': '64Mi'},
                                limits={'cpu': '1', 'memory': '64Mi'}
                            )
                        )
                    ]
                )
            )
        )
    )

    ns = args.namespace

    # Create the deployment
    print(f"Creating deployment 'ibench-cpu' with 1 replica in namespace '{ns}'...")
    try:
        apps_v1.create_namespaced_deployment(namespace=ns, body=deployment)
        print("Deployment created.")
    except client.exceptions.ApiException as e:
        if e.status == 409:
            print("Deployment already exists. Skipping creation.")
        else:
            raise

    # Scale to desired replicas
    target = args.replicas
    print(f"Scaling deployment to {target} replicas...")
    scale_body = {'spec': {'replicas': target}}
    apps_v1.patch_namespaced_deployment_scale(
        name='ibench-cpu', namespace=ns, body=scale_body
    )
    print("Scale request sent.")

    # Wait for specified delay
    print(f"Waiting {args.delay} seconds before deletion...")
    time.sleep(args.delay)

    # Delete the deployment
    print("Deleting deployment 'ibench-cpu'...")
    apps_v1.delete_namespaced_deployment(
        name='ibench-cpu',
        namespace=ns,
        body=client.V1DeleteOptions(
            propagation_policy='Foreground',
            grace_period_seconds=0
        )
    )
    print("Deployment deleted.")


if __name__ == '__main__':
    main()
