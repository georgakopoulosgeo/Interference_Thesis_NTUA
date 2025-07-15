from kubernetes import client, config

# --- Define the plan ---
Replica_Plan = {
    "minikube": 2,
    "minikube-m02": 1
}

DEPLOYMENT_NAME = "my-nginx"
NAMESPACE = "default"
LABEL_SELECTOR = "app=my-nginx"
NODE_LABEL_KEY = "kubernetes.io/hostname"

# --- Setup ---
config.load_kube_config()
apps_v1 = client.AppsV1Api()
core_v1 = client.CoreV1Api()


def patch_deployment_with_affinity(replica_plan: dict):
    """
    Scales deployment and enforces strict node placement using required affinity rules.
    """
    total_replicas = sum(replica_plan.values())

    # Build multiple nodeSelectorTerms, one for each node in the plan
    selector_terms = []
    for node, count in replica_plan.items():
        if count > 0:
            selector_terms.append({
                "matchExpressions": [{
                    "key": NODE_LABEL_KEY,
                    "operator": "In",
                    "values": [node]
                }]
            })

    patch_body = {
        "spec": {
            "replicas": total_replicas,
            "template": {
                "spec": {
                    "affinity": {
                        "nodeAffinity": {
                            "requiredDuringSchedulingIgnoredDuringExecution": {
                                "nodeSelectorTerms": selector_terms
                            }
                        }
                    }
                }
            }
        }
    }

    print(f"Applying plan: {replica_plan} (total replicas: {total_replicas})")
    apps_v1.patch_namespaced_deployment(
        name=DEPLOYMENT_NAME,
        namespace=NAMESPACE,
        body=patch_body
    )
    print("Deployment scaled and affinity patched.")


def evict_non_matching_pods(replica_plan: dict):
    """
    Evict pods that are not scheduled on nodes in the plan.
    """
    allowed_nodes = {node for node, count in replica_plan.items() if count > 0}

    pods = core_v1.list_namespaced_pod(
        namespace=NAMESPACE,
        label_selector=LABEL_SELECTOR
    ).items

    for pod in pods:
        node = pod.spec.node_name
        pod_name = pod.metadata.name

        if node not in allowed_nodes:
            print(f"Evicting pod {pod_name} from node {node}")
            core_v1.delete_namespaced_pod(
                name=pod_name,
                namespace=NAMESPACE,
                grace_period_seconds=0
            )


def main():
    patch_deployment_with_affinity(Replica_Plan)
    evict_non_matching_pods(Replica_Plan)


if __name__ == "__main__":
    main()
