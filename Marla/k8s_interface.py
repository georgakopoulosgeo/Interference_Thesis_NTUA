from kubernetes import client, config
from config import NAMESPACE, DEPLOYMENT_BASE, IMAGE, LABEL, NODE_LABEL_KEY
import logging
from time import sleep

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


def get_current_replicas(name: str) -> int:
    try:
        deployment = apps_v1.read_namespaced_deployment(name=name, namespace=NAMESPACE)
        return deployment.spec.replicas or 0
    except client.exceptions.ApiException as e:
        if e.status == 404:
            return 0
        else:
            logger.error(f"Failed to fetch deployment '{name}': {e}")
            raise

def apply_replica_plan(replica_plan: dict, delay_before_scale_down: int = 5):
    """
    Applies the given replica plan:
    - First scales up target nodes (to avoid cold starts)
    - Waits briefly before scaling down nodes
    - Avoids full evictions unless strictly needed
    """
    scale_up = []
    scale_down = []

    for node, desired_replicas in replica_plan.items():
        name = f"{DEPLOYMENT_BASE}-{node.replace('.', '-')}"
        current_replicas = get_current_replicas(name)

        # Decide whether to create, scale up or scale down
        if current_replicas == 0 and desired_replicas > 0:
            # Deployment may not exist, try to create it
            try:
                scale_body = {"spec": {"replicas": desired_replicas}}
                apps_v1.patch_namespaced_deployment_scale(name=name, namespace=NAMESPACE, body=scale_body)
                logger.info(f"🚀 Warm start: scaled up '{name}' to {desired_replicas}")
            except client.exceptions.ApiException as e:
                if e.status == 404:
                    deployment = build_deployment(node, name, desired_replicas)
                    apps_v1.create_namespaced_deployment(namespace=NAMESPACE, body=deployment)
                    logger.info(f"✅ Created & scaled '{name}' to {desired_replicas}")
                else:
                    logger.error(f"Failed to scale or create deployment '{name}': {e}")
                    raise
        elif desired_replicas > current_replicas:
            scale_up.append((name, desired_replicas))
        elif desired_replicas < current_replicas:
            scale_down.append((name, desired_replicas))
        else:
            logger.info(f"➖ No change needed for '{name}' ({current_replicas} replicas)")

    # Phase 1: Scale up
    for name, replicas in scale_up:
        scale_body = {"spec": {"replicas": replicas}}
        apps_v1.patch_namespaced_deployment_scale(name=name, namespace=NAMESPACE, body=scale_body)
        logger.info(f"⬆️ Scaled up: {name} to {replicas} replicas")

    # Wait before scaling down (let pods warm up)
    if scale_down:
        logger.info(f"⏳ Waiting {delay_before_scale_down}s before scaling down to avoid cold-start collisions...")
        sleep(delay_before_scale_down)

    # Phase 2: Scale down
    for name, replicas in scale_down:
        scale_body = {"spec": {"replicas": replicas}}
        apps_v1.patch_namespaced_deployment_scale(name=name, namespace=NAMESPACE, body=scale_body)
        if replicas == 0:
            logger.info(f"🌑 Idled deployment '{name}' (scaled to 0)")
        else:
            logger.info(f"⬇️ Scaled down: {name} to {replicas} replicas")


