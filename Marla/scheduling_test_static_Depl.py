from kubernetes import client, config

# ---------------------- CONFIG ---------------------- #
NAMESPACE = "default"
DEPLOYMENT_BASE = "my-nginx"
IMAGE = "nginx:1.21-alpine"
LABEL = {"app": "my-nginx"}  # Shared label for Service targeting
NODE_LABEL_KEY = "kubernetes.io/hostname"

# --- Define the replica plan here ---
Replica_Plan = {
    "minikube": 1,
    "minikube-m02": 2
}
# ---------------------------------------------------- #

# Load kubeconfig
config.load_kube_config()
apps_v1 = client.AppsV1Api()


def build_deployment_spec(node: str, replicas: int) -> client.V1DeploymentSpec:
    return client.V1DeploymentSpec(
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


def scale_or_create_deployments(replica_plan: dict):
    for node, replicas in replica_plan.items():
        deployment_name = f"{DEPLOYMENT_BASE}-{node.replace('.', '-')}"
        spec = build_deployment_spec(node, replicas)
        metadata = client.V1ObjectMeta(name=deployment_name, labels=LABEL)
        deployment = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=metadata,
            spec=spec
        )

        try:
            apps_v1.patch_namespaced_deployment(name=deployment_name, namespace=NAMESPACE, body=deployment)
            print(f"🔁 Scaled: {deployment_name} to {replicas} replicas on node '{node}'")
        except client.exceptions.ApiException as e:
            if e.status == 404:
                apps_v1.create_namespaced_deployment(namespace=NAMESPACE, body=deployment)
                print(f"✅ Created: {deployment_name} with {replicas} replicas on node '{node}'")
            else:
                raise


if __name__ == "__main__":
    scale_or_create_deployments(Replica_Plan)
