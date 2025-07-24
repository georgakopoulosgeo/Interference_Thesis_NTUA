import time
import logging
import json
from datetime import datetime, timezone
import sys
import os
from config import CHECK_INTERVAL_SEC
from arima import predict_next_rps, train_arima_model
from predictor_client import get_slowdown_predictions
from placement_logic import choose_best_replica_plan, determine_replica_count_for_rps
from k8s_interface import apply_replica_plan
#from utils import log_decision

logging.basicConfig(level=logging.INFO) # Logging setup
last_applied_plan = None

def log_replica_plan(log_path, rps, replicas, plan):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rps": rps,
        "desired_replicas": replicas,
        "replica_distribution": plan
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")



def marla_loop(log_path):
    last_applied_plan = {"minikube": 1,"minikube-m02": 1} # Initial state with 1 replica on each node
    while True:
        start_time = time.time()
        logging.info("Controller loop triggered.")
        # 1. Ensure model is trained before predictions
        train_arima_model()  

        try:
            # 2. Forecast next-minute RPS
            forecasted_rps = predict_next_rps()
            logging.info(f"Forecasted RPS: {forecasted_rps}")
            forecasted_rps_round200 = round(forecasted_rps / 200) * 200 # Round to nearest 200 for Lookup Table
            forecasted_rps_round500 = round(forecasted_rps / 500) * 500 # Round to nearest 500 for slowdown predictions

            # 3. Get number of replicas needed based on forecasted RPS, from the lookup table
            replicas_needed = determine_replica_count_for_rps(forecasted_rps_round200)
            logging.info(f"Replicas needed based on forecasted RPS: {replicas_needed}")

            # 4. Get normalized_perfomance predictions for each combination of pods in the nodes. 
            normalized_perfomance_predictions = get_slowdown_predictions(forecasted_rps_round500, replicas_needed)
            #logging.info(f"Slowdown predictions: {normalized_perfomance_predictions}")

            # 5. Choose optimal replica plan
            best_plan = choose_best_replica_plan(normalized_perfomance_predictions, replicas_needed, last_applied_plan)
            logging.info(f"Best replica plan selected: {best_plan}")

            # 6. Apply changes if different from current distribution
            if best_plan != last_applied_plan:
                apply_replica_plan(best_plan)
                last_applied_plan = best_plan
                logging.info("Applied new replica plan.")
            else:
                logging.info("Current plan already optimal. No changes made.")
            log_replica_plan(log_path, f"{forecasted_rps}_{forecasted_rps_round500}", replicas_needed, best_plan)

            # Log decision
            #log_decision(forecasted_rps, slowdown_predictions, last_applied_plan, best_plan)

        except Exception as e:
            logging.error(f"Controller error: {e}")

        # Wait until next minute
        elapsed = time.time() - start_time
        time.sleep(max(0, CHECK_INTERVAL_SEC - elapsed))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 marla_loop.py <interference_filename>")
        sys.exit(1)

    log_filename = sys.argv[1]
    log_path = os.path.join("/home/george/logs/marla", log_filename)
    os.makedirs("/home/george/logs/marla", exist_ok=True)
    if not log_path.endswith(".jsonl"):
        log_path += ".jsonl"


    marla_loop(log_path)
