import requests
import logging
from config import PREDICTOR_API_URL

# Query the slowdown predictor API with RPS and candidate replica counts.
def get_slowdown_predictions(forecasted_rps: int, replicas_needed: list[int]) -> dict:
    try:
        payload = {
            "rps": forecasted_rps,
            "replicas": replicas_needed
        }

        response = requests.post(f"{PREDICTOR_API_URL}/predict", json=payload, timeout=5)
        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:
        logging.error(f"Error contacting slowdown predictor API: {e}")
        return {}  # Fallback: empty dict (no predictions)
'''
    Returns:
        A dict of the form:
        {
            1: {'node1': 0.6, 'node2': 0.8},
            2: {'node1': 0.55, 'node2': 0.75},
            ...
        }
'''