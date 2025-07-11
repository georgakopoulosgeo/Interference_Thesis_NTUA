COOLDOWN_PERIOD = 3  # minutes between major actions
SLO_THRESHOLD = 0.8  # Acceptable slowdown ratio
MAX_REPLICAS = 4

RPS_TO_REPLICAS = {
    0: 1,
    1500: 2,
    3000: 3,
    4000: 4
}

CLUSTER_NODES = ['node1', 'node2']
