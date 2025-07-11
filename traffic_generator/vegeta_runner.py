import subprocess

def run_vegeta_attack(rps, duration=60, target_url="http://nginx.default.svc.cluster.local"):
    """
    Executes a Vegeta load test at the specified RPS for 60 seconds.

    - Uses `echo` to pipe a GET target into vegeta
    - Uses subprocess to shell out to vegeta
    - Saves metrics and binary output to logs/

    Arguments:
    - rps: int – requests per second
    - duration: int – test duration in seconds
    - target_url: str – URL to hit (Kubernetes Service)

    Returns: None
    """
