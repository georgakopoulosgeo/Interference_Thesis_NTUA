import itertools

def compute_aggregated_performance(plan: dict, predictions: dict, method: str) -> float:
    active_scores = []
    total_replicas = sum(plan.values())
    
    if total_replicas == 0:
        return float('-inf')

    weighted_sum = 0.0
    
    for node, r in plan.items():
        if r > 0:
            nps = predictions.get(r, {}).get(node, 1.0)
            active_scores.append(nps)
            weighted_sum += r * nps

    if method == "avg":
        return weighted_sum / total_replicas
    elif method == "maxmin":
        return min(active_scores) if active_scores else float('-inf')
    else:
        raise ValueError(f"Unsupported method: {method}")

def choose_best_replica_plan(np_predictions: dict, nodes: list, replicas_needed: int, method: str) -> tuple:
    best_plan = None
    best_score = -float('inf')
    
    for combo in itertools.product(range(replicas_needed + 1), repeat=len(nodes)):
        if sum(combo) != replicas_needed:
            continue
            
        current_plan = {nodes[i]: combo[i] for i in range(len(nodes))}
        score = compute_aggregated_performance(current_plan, np_predictions, method=method)
        
        if score > best_score:
            best_score = score
            best_plan = current_plan

    return best_plan, best_score

def print_plan_latency_profile(plan: dict, predictions: dict, baseline_latency: float):
    """
    Calculates and prints the real p99 latency profile.
    Highlights the maximum bottleneck latency which dictates the cluster's true tail performance.
    """
    print("  -> Latency Profile per Node:")
    active_latencies = []
    
    for node, r in plan.items():
        if r > 0:
            nps = predictions[r][node]
            observed_p99 = baseline_latency / nps
            active_latencies.append(observed_p99)
            print(f"     * {node}: {r} replica(s) | NPS = {nps:.2f} | Expected Node p99 = {observed_p99:.2f} ms")
        else:
            print(f"     * {node}: 0 replicas   | NPS = N/A  | Expected Node p99 = 0.00 ms (No Traffic)")
            
    if active_latencies:
        # The cluster's tail latency is bounded by the worst performing component
        global_p99_bottleneck = max(active_latencies)
        print(f"\n  🔥 TRUE APPLICATION TAIL BOUND: {global_p99_bottleneck:.2f} ms")
        print("     (Do NOT average percentiles. Your application's global p99 will trend")
        print(f"     towards this worst-case node because it processes an equal share of traffic.)")

if __name__ == "__main__":
    cluster_nodes = ["node1", "node2", "node3"]
    replicas_demanded = 3
    baseline_p99 = 2.0  # 2ms isolated baseline latency

    example_predictions = {
        1: {"node1": 0.98, "node2": 0.98, "node3": 0.45},  
        2: {"node1": 0.70, "node2": 0.70, "node3": 0.30},  
        3: {"node1": 0.55, "node2": 0.55, "node3": 0.10},  
    }

    print(f"--- TESTING DEMAND: {replicas_demanded} REPLICAS (Baseline Isolated p99 = {baseline_p99} ms) ---")

    # 1. Run Flawed Average Metric
    avg_plan, avg_score = choose_best_replica_plan(example_predictions, cluster_nodes, replicas_demanded, method="avg")
    print("\n[FLAWED] Paper's 'avg' Metric Result:")
    print(f"  -> Chosen Plan:  {avg_plan}")
    print(f"  -> Metric Score: {avg_score:.4f}")
    print_plan_latency_profile(avg_plan, example_predictions, baseline_p99)
    print("  ❌ CRITICAL FAILURE: Look at node3. Because the 'avg' metric covers up the failure,")
    print("     33% of your load-balanced traffic is experiencing a massive 4.44 ms tail latency spike,")
    print("     which completely destroys your p99 target cluster-wide.")

    print("\n" + "-" * 75)

    # 2. Run Corrected Max-Min Metric
    mm_plan, mm_score = choose_best_replica_plan(example_predictions, cluster_nodes, replicas_demanded, method="maxmin")
    print("\n[CORRECT] Corrected 'maxmin' Metric Result:")
    print(f"  -> Chosen Plan:  {mm_plan}")
    print(f"  -> Metric Score: {mm_score:.4f}")
    print_plan_latency_profile(mm_plan, example_predictions, baseline_p99)
    print("  ✅ SUCCESS: Max-Min kept all traffic away from node3.")
    print("     The worst-case latency any user will experience is capped at 2.86 ms on node1.")
    print("     Your tail latency remains tight, bounded, and safe from noisy neighbors.")