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


def delete_old_deployments():
    deployments = apps_v1.list_namespaced_deployment(namespace=NAMESPACE).items
    for dep in deployments:
        if dep.metadata.name.startswith(DEPLOYMENT_BASE + "-"):
            apps_v1.delete_namespaced_deployment(
                name=dep.metadata.name,
                namespace=NAMESPACE,
                grace_period_seconds=0
            )
            print(f"Deleted old deployment: {dep.metadata.name}")


def build_deployment(name: str, node: str, replicas: int) -> client.V1Deployment:
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


def apply_precise_deployments(replica_plan: dict):
    for node, count in replica_plan.items():
        if count == 0:
            continue
        deployment_name = f"{DEPLOYMENT_BASE}-{node.replace('.', '-')}"
        deployment = build_deployment(deployment_name, node, count)

        try:
            apps_v1.create_namespaced_deployment(namespace=NAMESPACE, body=deployment)
            print(f"✅ Created: {deployment_name} with {count} replicas on node '{node}'")
        except client.exceptions.ApiException as e:
            if e.status == 409:
                apps_v1.replace_namespaced_deployment(name=deployment_name, namespace=NAMESPACE, body=deployment)
                print(f"♻️ Updated: {deployment_name} with {count} replicas on node '{node}'")
            else:
                raise


if __name__ == "__main__":
    delete_old_deployments()  # Optional: remove previous per-node deploys
    apply_precise_deployments(Replica_Plan)
