from config import PLACEMENT_METRIC
import logging
from typing import Dict
import json

logging.basicConfig(level=logging.INFO)  # Logging setup

def compute_aggregated_performance(r1, np1, r2, np2, method="avg"):
    """
    Calculates the aggregated perfomance of a replica_plan.
    Each replica_plan is described with 4 values: 
        r1: number of replicas in node 1
        np1: normalized perfomance of replicas in node1 (for all r1 replicas, not individually)
        r2: number of replicas in node2
        np2: normalized perfomance of replicas in node2
    
    Returns the Score for this replica plan
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
    
    # Πιθανόν να ευνοεί τις περιπτώσεις με 0 replicas σε εναν κομβο

# Selects the best replica combination that maximizes aggregated normalized performance.
def choose_best_replica_plan(np_predictions_raw: Dict[int, Dict[str, float]],replicas_needed: int,prev_plan: Dict[str, int], empty_node_penalty: float = 0.2) -> Dict[str, int]:
    np_predictions = {int(k): v for k, v in np_predictions_raw.items()}
    best_plan = None
    best_score = -float('inf')

    total_replicas_options = [replicas_needed]
    if replicas_needed > 1:
        total_replicas_options.append(replicas_needed - 1)
    
    # Basically if we have replicas_needed = 3, we will try all combinations of  
    # (0, 2), (2, 0), (1, 1), 
    # (0, 3), (3, 0), (1, 2), (2, 1)

    for total_replicas in total_replicas_options:
        for r1 in range(0, total_replicas + 1):
            r2 = total_replicas - r1

            # Skip if slowdown predictions are unavailable
            if (r1 != 0 and r1 not in np_predictions) or (r2 != 0 and r2 not in np_predictions):
                continue

            np1 = np_predictions.get(r1, {}).get('node1', 0.0) if r1 > 0 else 0.0
            np2 = np_predictions.get(r2, {}).get('node2', 0.0) if r2 > 0 else 0.0

            score = compute_aggregated_performance(r1, np1, r2, np2, method=PLACEMENT_METRIC)
            logging.debug(f"Evaluating plan: r1={r1} np1={np1:.3f}, r2={r2} np2={np2:.3f} -> Score before penalty: {score:.4f}")

            # Penalty for fully emptying a node
            if r1 == 0 or r2 == 0:
                score -= empty_node_penalty
                logging.debug(f"Penalty applied for empty node → New Score: {score:.4f}")

            if score > best_score:
                best_score = score
                best_plan = {'minikube': r1, 'minikube-m02': r2}

    return best_plan




# Get the number of replicas needed based on forecasted RPS from the replica_lookup.json file
def determine_replica_count_for_rps(predicted_rps: int) -> int:
    try:
        with open("replica_lookup.json", "r") as f:
            lookup_table = json.load(f)

        # Sort by rps 
        sorted_table = sorted(lookup_table, key=lambda x: x["RPS"])

        recommended = None
        for entry in sorted_table:
            if entry["RPS"] <= predicted_rps:
                recommended = entry["Recommended_Replicas"]
            else:
                break

        if recommended is not None:
            return recommended
        else:
            # Fallback: return minimum available recommendation
            return sorted_table[0]["Recommended_Replicas"]

    except Exception as e:
        print(f"❌ Failed to determine replica count: {e}")
        return 1  # Safe fallback   

if __name__ == "__main__":
    # Example usage
    example_predictions = {
        1: {"node1": 0.91, "node2": 0.95},
        2: {"node1": 0.75, "node2": 0.85},
        3: {"node1": 0.80, "node2": 0.90}
    }
    
    best_plan = choose_best_replica_plan(example_predictions)
    print(f"Best replica plan: {best_plan}")
    
    rps = 1700
    replicas_needed = determine_replica_count_for_rps(rps)
    print(f"Replicas needed for RPS {rps}: {replicas_needed}")


"""
NOTES

predictions_raw:
{
    1: {"node1": 0.91, "node2": 0.95},
    2: {"node1": 0.75, "node2": 0.85}, etc
}


    # Number of Checks:
    # 1. Summation formula:
    #   Total = Sum from i=1 to N of (i + 1) = (N^2 + 3N - 2)/2
    # 2. Binomial coefficient formula:
    #   Total = C(N + 2, 2) - 1 = [(N + 1)(N + 2)]/2 - 1
"""