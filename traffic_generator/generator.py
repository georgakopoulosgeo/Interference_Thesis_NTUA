import random
from typing import List, Optional

def run_traffic_test():
    """
    1. Generates 30-minute RPS schedule (1 step per minute)
    2. For each minute:
       - Runs vegeta attack
       - Parses vegeta results (latency, throughput)
       - Logs current RPS + metrics
    3. Saves RPS schedule + metrics log at the end
    """

def generate_rps_schedule(
    duration_minutes: int = 30,
    base_rps: int = 1500,
    mode: str = "random",
    predefined_rps: Optional[List[int]] = None
) -> List[int]:
    """
    Generates a per-minute RPS schedule.

    Parameters:
        - duration_minutes: total test time in minutes
        - base_rps: starting RPS for random mode
        - mode: "random" or "predefined"
        - predefined_rps: list of RPS levels (only for predefined mode)

    Returns:
        List[int]: length == duration_minutes
    """
    if mode == "random":
        rps_values = [base_rps]
        for _ in range(1, duration_minutes):
            delta = random.choice([-500, -200, 200, 500])
            next_rps = max(500, min(4000, rps_values[-1] + delta))
            rps_values.append(next_rps)
        return rps_values

    elif mode == "predefined":
        if not predefined_rps:
            raise ValueError("You must provide a list of RPS levels for 'predefined' mode.")
        
        rps_values = []
        for rps_level in predefined_rps:
            rps_values.extend([rps_level] * 2)  # Each value held for 2 minutes
        # If list is too short or too long, trim or extend
        return (rps_values + [predefined_rps[-1]] * duration_minutes)[:duration_minutes]

    else:
        raise ValueError("Mode must be either 'random' or 'predefined'")