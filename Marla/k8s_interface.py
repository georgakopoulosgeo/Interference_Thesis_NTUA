def scale_nginx_deployment(new_replica_count):
    """
    Updates the number of replicas for the Nginx deployment.
    Uses the Kubernetes API to patch the deployment spec.
    """

def evict_nginx_pods_from_node(node_name, num_to_evict):
    """
    Forcefully evicts a number of Nginx pods from a specific node.
    Allows controlled reshuffling of placement.
    """

def set_node_affinity_for_nginx(preferred_node_distribution):
    """
    Modifies affinity rules to guide Kubernetes in scheduling Nginx replicas
    to the preferred nodes.
    """

def get_current_nginx_pod_distribution():
    """
    Returns the current number of Nginx pods per node.
    Used to determine placement delta.
    Returns: dict[node_name] = num_pods
    """

def get_all_nginx_pods():
    """
    Returns metadata (name, node, status) for all running Nginx pods.
    Used by eviction logic and replica mapping.
    """
