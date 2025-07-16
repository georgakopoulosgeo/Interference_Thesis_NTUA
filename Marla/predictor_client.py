def format_input_vector(metrics, rps, replicas):
    """
    Prepares input features for the slowdown predictor.
    Combines metrics + rps + replica count into one feature vector per node.
    Returns: dict[node_name] = [feature1, feature2, ..., featureN]
    """

def query_slowdown_predictor(input_vector):
    """
    Sends a POST request to the slowdown predictor API.
    Returns: dict[node_name] = predicted slowdown (float between 0 and 1)
    """

def get_predictions_for_all_placements(metrics, predicted_rps, placement_options):
    """
    Loops over possible replica placements and gets predicted slowdown for each.
    Returns: dict[placement] = {node1: slowdown1, node2: slowdown2}
    """
