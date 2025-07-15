from kubernetes import client, config

DEPLOYMENT_NAME = "my-nginx"
NAMESPACE = "default"
TARGET_NODE = "minikube"
REPLICAS = 3

def enforce_strict_node_affinity(api):
    # Patch the deployment with required nodeAffinity for node1
    patch_body = {
        "spec": {
            "replicas": REPLICAS,
            "template": {
                "spec": {
                    "affinity": {
                        "nodeAffinity": {
                            "requiredDuringSchedulingIgnoredDuringExecution": {
                                "nodeSelectorTerms": [
                                    {
                                        "matchExpressions": [
                                            {
                                                "key": "kubernetes.io/hostname",
                                                "operator": "In",
                                                "values": [TARGET_NODE]
                                            }
                                        ]
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }
    }

    api.patch_namespaced_deployment(
        name=DEPLOYMENT_NAME,
        namespace=NAMESPACE,
        body=patch_body
    )
    print(f"Deployment patched: forced all replicas to node '{TARGET_NODE}'.")

def evict_wrong_pods(core_api):
    # List all pods and delete any that are not on node1
    pods = core_api.list_namespaced_pod(
        namespace=NAMESPACE,
        label_selector="app=my-nginx"
    ).items

    for pod in pods:
        if pod.spec.node_name != TARGET_NODE:
            print(f"Evicting pod {pod.metadata.name} from node {pod.spec.node_name}")
            core_api.delete_namespaced_pod(
                name=pod.metadata.name,
                namespace=NAMESPACE,
                grace_period_seconds=0
            )

def main():
    config.load_kube_config()
    apps_v1 = client.AppsV1Api()
    core_v1 = client.CoreV1Api()

    enforce_strict_node_affinity(apps_v1)
    evict_wrong_pods(core_v1)

if __name__ == "__main__":
    main()
