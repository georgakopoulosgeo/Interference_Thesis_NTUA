from kubernetes import client, config

NAMESPACE = "default"
DEPLOYMENT_BASE = "my-nginx"
IMAGE = "nginx:1.21-alpine"
LABEL = {"app": "my-nginx"}
NODE_LABEL_KEY = "kubernetes.io/hostname"

Replica_Plan = {
    "minikube": 1,
    "minikube-m02": 0  # Will trigger deletion
}

config.load_kube_config()
apps_v1 = client.AppsV1Api()

# Builds a Kubernetes Deployment object for the given node and replica count.
# Used only when a deployment for the specified node does not exist and needs to be created from scratch.
def build_deployment(node: str, name: str, replicas: int) -> client.V1Deployment:
    return client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=name, labels=LABEL),
        spec=client.V1DeploymentSpec(
            replicas=replicas,
            selector=client.V1LabelSelector(match_labels=LABEL),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels=LABEL),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="nginx",
                            image=IMAGE,
                            ports=[client.V1ContainerPort(container_port=80)],
                            resources=client.V1ResourceRequirements(
                                requests={"cpu": "500m", "memory": "512Mi"},
                                limits={"cpu": "500m", "memory": "512Mi"}
                            )
                        )
                    ],
                    affinity=client.V1Affinity(
                        node_affinity=client.V1NodeAffinity(
                            required_during_scheduling_ignored_during_execution=client.V1NodeSelector(
                                node_selector_terms=[
                                    client.V1NodeSelectorTerm(
                                        match_expressions=[
                                            client.V1NodeSelectorRequirement(
                                                key=NODE_LABEL_KEY,
                                                operator="In",
                                                values=[node]
                                            )
                                        ]
                                    )
                                ]
                            )
                        )
                    )
                )
            )
        )
    )


# Applies the given replica plan by scaling existing deployments, deleting those with 0 replicas, or creating new ones.
# Used as the main function to orchestrate scaling, creation, or deletion based on the current per-node replica requirements.
def apply_replica_plan(replica_plan: dict):
    for node, replicas in replica_plan.items():
        name = f"{DEPLOYMENT_BASE}-{node.replace('.', '-')}"
        if replicas == 0:
            # If replicas are 0, delete the deployment if it exists
            try:
                apps_v1.delete_namespaced_deployment(name=name, namespace=NAMESPACE, grace_period_seconds=0)
                print(f"🗑️ Deleted deployment '{name}' (replicas=0)")
            except client.exceptions.ApiException as e:
                if e.status != 404:
                    raise
        else:
            # If replicas > 0, try to scale the deployment
            try:
                scale = {"spec": {"replicas": replicas}}
                apps_v1.patch_namespaced_deployment_scale(name=name, namespace=NAMESPACE, body=scale)
                print(f"🔁 Scaled: {name} to {replicas} replicas")
            except client.exceptions.ApiException as e:
                if e.status == 404:
                    # If deployment does not exist, create it
                    deployment = build_deployment(node, name, replicas)
                    apps_v1.create_namespaced_deployment(namespace=NAMESPACE, body=deployment)
                    print(f"✅ Created: {name} with {replicas} replicas on node '{node}'")
                else:
                    raise


if __name__ == "__main__":
    apply_replica_plan(Replica_Plan)
