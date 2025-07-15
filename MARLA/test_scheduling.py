from kubernetes import client, config

# Configuration
DEPLOYMENT_NAME = "my-nginx"           # Change to your deployment name
NAMESPACE = "default"               # Change if needed
REPLICAS = 4
NODE_1 = "minikube"
NODE_2 = "minikube-m02"

def create_affinity_patch(node_name):
    return {
        "weight": 100,
        "preference": {
            "matchExpressions": [
                {
                    "key": "kubernetes.io/hostname",
                    "operator": "In",
                    "values": [node_name]
                }
            ]
        }
    }

def patch_deployment_with_affinity(api_instance):
    affinity_patch = {
        "spec": {
            "replicas": REPLICAS,
            "template": {
                "spec": {
                    "affinity": {
                        "nodeAffinity": {
                            "preferredDuringSchedulingIgnoredDuringExecution": [
                                create_affinity_patch(NODE_1),
                                create_affinity_patch(NODE_2)
                            ]
                        }
                    }
                }
            }
        }
    }

    print(f"Patching deployment '{DEPLOYMENT_NAME}' with node affinity for 2 nodes...")
    api_instance.patch_namespaced_deployment(
        name=DEPLOYMENT_NAME,
        namespace=NAMESPACE,
        body=affinity_patch
    )
    print("Affinity patched and replicas scaled.")

def main():
    config.load_kube_config()
    apps_v1 = client.AppsV1Api()

    patch_deployment_with_affinity(apps_v1)

if __name__ == "__main__":
    main()
