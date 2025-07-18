from config import RPS_TO_REPLICAS, MAX_REPLICAS, PLACEMENT_METRIC
import logging
logging.basicConfig(level=logging.INFO) # Logging setup

def compute_aggregated_slowdown(r1, s1, r2, s2, method="avg"):
    # Aggregates the slowdowns 
    # Options: either weighted average or max.
    # Args:
    #    r1, r2: Replica counts on node1 and node2
    #    s1, s2: Predicted slowdowns on node1 and node2
    #    method: 'avg' (weighted average) or 'max' (worst-case)
    if method == "avg":
        total = r1 + r2
        if total == 0:
            return float('inf')
        return (r1 * s1 + r2 * s2) / total
    elif method == "max":
        if r1 == 0:
            return s2
        elif r2 == 0:
            return s1
        return max(s1, s2)
    else:
        raise ValueError(f"Unsupported slowdown aggregation method: {method}")


def choose_best_replica_plan(slowdown_predictions: dict) -> dict:
    """
    Selects the best replica placement across nodes that minimizes aggregated slowdown.
    Evaluates all valid splits of total replicas across the two nodes and choose the best.
    Example: 
        slowdown_predictions:
            {
                1: {"node1": 0.91, "node2": 0.95},
                2: {"node1": 0.75, "node2": 0.85},
                3: {"node1": 0.6, "node2": 0.78},
                4: {"node1": 0.52, "node2": 0.72}
            }
        Calculation: 
        For each total_replica count N, we evaluate all (r1, r2) such that r1 + r2 = N.
        For each split, s1 is slowdown_predictions[r1]['node1']
                        s2 is slowdown_predictions[r2]['node2']

    Returns:
        {'minikube': best_r1, 'minikube-m02': best_r2}
    """
    best_plan = None
    best_score = -float('inf')

    available_replica_counts = sorted(int(k) for k in slowdown_predictions.keys())

    for total_replicas in available_replica_counts:
        for r1 in range(0, total_replicas + 1):
            r2 = total_replicas - r1

            # Skip splits for which we don't have predictions
            if r1 not in slowdown_predictions or r2 not in slowdown_predictions:
                continue

            s1 = slowdown_predictions.get(r1, {}).get('node1', 0.0) if r1 > 0 else 0.0
            s2 = slowdown_predictions.get(r2, {}).get('node2', 0.0) if r2 > 0 else 0.0

            score = compute_aggregated_slowdown(r1, s1, r2, s2, method=PLACEMENT_METRIC)
            # Logging the score for debugging
            logging.info(f"Evaluating split: ({r1}, {r2}) -> Score: {score}")

            if score > best_score:
                best_score = score
                best_plan = {'minikube': r1, 'minikube-m02': r2}

    return best_plan


def determine_replica_count_for_rps(predicted_rps):
    """
    Uses the lookup table to determine the number of replicas
    needed for the expected traffic.
    Returns: int
    """
    return RPS_TO_REPLICAS.get(predicted_rps, MAX_REPLICAS)
