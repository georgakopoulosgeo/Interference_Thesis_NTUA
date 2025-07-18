from config import RPS_TO_REPLICAS, MAX_REPLICAS, PLACEMENT_METRIC
import logging
from typing import Dict

logging.basicConfig(level=logging.INFO)  # Logging setup

def compute_aggregated_performance(r1, np1, r2, np2, method="avg"):
    """
    Aggregates normalized performance values (np1, np2) using:
    - Weighted average ('avg')
    - Maximum ('max')
    """
    if method == "avg":
        total = r1 + r2
        if total == 0:
            return float('-inf')
        return (r1 * np1 + r2 * np2) / total
    elif method == "max":
        if r1 == 0:
            return np2
        elif r2 == 0:
            return np1
        return max(np1, np2)
    else:
        raise ValueError(f"Unsupported performance aggregation method: {method}")


def choose_best_replica_plan(np_predictions_raw: Dict[int, Dict[str, float]]) -> Dict[str, int]:
    """
    Selects the best replica placement that maximizes aggregated normalized performance.
    
    Args:
        np_predictions_raw:
            {
                1: {"node1": 0.91, "node2": 0.95},
                2: {"node1": 0.75, "node2": 0.85},
                ...
            }

    Returns:
        {'minikube': best_r1, 'minikube-m02': best_r2}
    """
    # Ensure keys are integers in case the input comes from JSON
    np_predictions = {int(k): v for k, v in np_predictions_raw.items()}

    best_plan = None
    best_score = -float('inf')  # because we are maximizing normalized performance

    available_replica_counts = sorted(np_predictions.keys())

    for total_replicas in available_replica_counts:
        for r1 in range(0, total_replicas + 1):
            r2 = total_replicas - r1

            # Ensure predictions exist for each partial replica count
            if (r1 != 0 and r1 not in np_predictions) or (r2 != 0 and r2 not in np_predictions):
                continue

            np1 = np_predictions.get(r1, {}).get('node1', 0.0) if r1 > 0 else 0.0
            np2 = np_predictions.get(r2, {}).get('node2', 0.0) if r2 > 0 else 0.0

            score = compute_aggregated_performance(r1, np1, r2, np2, method=PLACEMENT_METRIC)

            logging.debug(f"Evaluated (r1={r1}, np1={np1:.3f}, r2={r2}, np2={np2:.3f}) → score={score:.4f}")

            if score > best_score:
                best_score = score
                best_plan = {'minikube': r1, 'minikube-m02': r2}

    return best_plan


def determine_replica_count_for_rps(predicted_rps: int) -> int:
    """
    Returns the recommended number of replicas based on predicted RPS.
    Falls back to MAX_REPLICAS if no exact match is found.
    """
    return RPS_TO_REPLICAS.get(predicted_rps, MAX_REPLICAS)
