# test_choose_plan.py

from typing import Dict

PLACEMENT_METRIC = "avg"  # or "max"

def compute_aggregated_slowdown(r1, s1, r2, s2, method="avg"):
    if method == "avg":
        total = r1 + r2
        if total == 0:
            return float('-inf')
        return (r1 * s1 + r2 * s2) / total
    elif method == "max":
        if r1 == 0:
            return s2
        elif r2 == 0:
            return s1
        return max(s1, s2)
    else:
        raise ValueError("Unsupported method")

def choose_best_replica_plan(slowdown_predictions_raw: Dict[int, Dict[str, float]]) -> Dict[str, int]:
    slowdown_predictions = {int(k): v for k, v in slowdown_predictions_raw.items()}

    best_plan = None
    best_score = -float('inf')

    available_counts = sorted(slowdown_predictions.keys())
    print (f"Available counts: {available_counts}")

    for total_replicas in available_counts:
        for r1 in range(0, total_replicas + 1):
            r2 = total_replicas - r1
            print(f"Evaluating plan r1={r1}, r2={r2}")

            if (r1 != 0 and r1 not in slowdown_predictions) or (r2 != 0 and r2 not in slowdown_predictions):
                continue

            s1 = slowdown_predictions.get(r1, {}).get('node1', 0.0) if r1 > 0 else 0.0
            s2 = slowdown_predictions.get(r2, {}).get('node2', 0.0) if r2 > 0 else 0.0

            score = compute_aggregated_slowdown(r1, s1, r2, s2, method=PLACEMENT_METRIC)

            print(f"Evaluated plan r1={r1}, r2={r2} → score={score:.4f}")

            if score > best_score:
                best_score = score
                best_plan = {'node1': r1, 'node2': r2}

    return best_plan


# === Run the test ===

input_data = {
    '1': {'node1': 0.8994756119183893, 'node2': 0.9410984771711695},
    '2': {'node1': 0.9073052165981178, 'node2': 1.0}
}

best = choose_best_replica_plan(input_data)
print("\n✅ Best plan selected:", best)
