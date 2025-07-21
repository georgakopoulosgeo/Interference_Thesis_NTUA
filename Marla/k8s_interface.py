from kubernetes import client, config
from config import NAMESPACE, DEPLOYMENT_BASE, IMAGE, LABEL, NODE_LABEL_KEY
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load kube config once
config.load_kube_config()
apps_v1 = client.AppsV1Api()

def build_deployment(node: str, name: str, replicas: int) -> client.V1Deployment:
    """Builds a new Deployment for the given node with specified replicas."""
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

def apply_replica_plan(replica_plan: dict):
    """
    Applies the given replica plan:
    - Scales existing deployments to the desired replica count (including 0)
    - Creates deployments if missing
    """
    for node, replicas in replica_plan.items():
        name = f"{DEPLOYMENT_BASE}-{node.replace('.', '-')}"
        scale_body = {"spec": {"replicas": replicas}}

        try:
            # Try to scale an existing deployment
            apps_v1.patch_namespaced_deployment_scale(name=name, namespace=NAMESPACE, body=scale_body)
            if replicas == 0:
                logger.info(f"🌑 Idling deployment '{name}' (scaled to 0)")
            else:
                logger.info(f"🔁 Scaled: {name} to {replicas} replicas")
        except client.exceptions.ApiException as e:
            if e.status == 404:
                # If deployment does not exist, create it with the desired replicas
                deployment = build_deployment(node, name, replicas)
                apps_v1.create_namespaced_deployment(namespace=NAMESPACE, body=deployment)
                logger.info(f"✅ Created: {name} with {replicas} replicas on node '{node}'")
            else:
                logger.error(f"Failed to scale or create deployment '{name}': {e}")
                raise

