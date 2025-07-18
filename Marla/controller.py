import time
import logging
from config import CHECK_INTERVAL_SEC, RPS_TO_REPLICAS, MAX_REPLICAS
from arima import predict_next_rps
from predictor_client import get_slowdown_predictions
from placement_logic import choose_best_replica_plan, determine_replica_count_for_rps
from k8s_interface import apply_replica_plan
#from utils import log_decision

logging.basicConfig(level=logging.INFO) # Logging setup

last_applied_plan = {"minikube": 1,"minikube-m02": 1} # Initial state with 1 replica on each node

def marla_loop():
    while True:
        start_time = time.time()
        logging.info("Controller loop triggered.")

        try:
            # Forecast next-minute RPS
            forecasted_rps = predict_next_rps()
            logging.info(f"Forecasted RPS: {forecasted_rps}")
            # Round to nearest 500 for consistency
            forecasted_rps = round(forecasted_rps / 500) * 500

            # Get number of replicas needed based on forecasted RPS, from the lookup table
            replicas_needed = determine_replica_count_for_rps(forecasted_rps)
            logging.info(f"Replicas needed based on forecasted RPS: {replicas_needed}")

            # Get slowdown predictions for each combination of pods in the nodes. 
            slowdown_predictions = get_slowdown_predictions(forecasted_rps, replicas_needed)
            logging.info(f"Slowdown predictions: {slowdown_predictions}")

            # Choose optimal replica plan
            best_plan = choose_best_replica_plan(slowdown_predictions)
            logging.info(f"Best replica plan selected: {best_plan}")

            # Apply changes if different from current distribution
            if best_plan != last_applied_plan:
                #apply_replica_plan(best_plan, forecasted_rps)
                #last_applied_plan = best_plan
                logging.info("Applied new replica plan.")
            else:
                logging.info("Current plan already optimal. No changes made.")

            # Log decision
            #log_decision(forecasted_rps, slowdown_predictions, last_applied_plan, best_plan)

        except Exception as e:
            logging.error(f"Controller error: {e}")

        # Wait until next minute
        elapsed = time.time() - start_time
        time.sleep(max(0, CHECK_INTERVAL_SEC - elapsed))

if __name__ == "__main__":
    marla_loop()

def measure_current_rps():
    """
    Measures or retrieves the current RPS observed by the system.
    Used to train ARIMA and estimate load.
    Returns: int
    """

def apply_best_placement(new_placement, current_placement):
    """
    Applies changes to the replica placement only if it differs from the current one.
    Performs eviction, scaling, and affinity patching.
    """

def should_act(current_placement, new_placement, last_action_time):
    """
    Decides whether to perform a new placement action based on:
    - Cooldown threshold
    - Meaningful difference in performance
    Returns: bool
    """

def log_state_and_decision():
    """
    Logs the full state, predictions, and decision to logs/ folder.
    Called at every MARLA iteration.
    """
