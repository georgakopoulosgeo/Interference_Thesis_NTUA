import json
import time
from datetime import datetime, timezone
from statsmodels.tsa.arima.model import ARIMA
import numpy as np

def get_rps_history():
    # Current approach: Get last rps from /home/george/logs/traffic_generator/rps_schedule.jsonl
    # Proper approach: Retrieves the historical RPS data with a query to Nginx Exporter (httptotalrequests)
    rps_history = []
    try:
        with open("/home/george/logs/traffic_generator/rps_schedule.jsonl", "r") as f:
            for line in f:
                entry = json.loads(line)
                rps_history.append(entry["rps"])
    except Exception as e:
        print(f"⚠️ Error reading RPS history: {e}")
    return rps_history



# Global model object
arima_model = None

#Trains an ARIMA model on the historical RPS data.
def train_arima_model():
    global arima_model
    rps_history = get_rps_history()

    if len(rps_history) < 10:
        print("Not enough data to train ARIMA model.")
        return

    try:
        # Check timestamp of the last entry
        with open("/home/george/logs/traffic_generator/rps_schedule.jsonl", "r") as f:
            last_line = list(f)[-1]
            last_entry = json.loads(last_line)
            last_time = datetime.fromisoformat(last_entry["timestamp"])
            now = datetime.now(timezone.utc)
            time_diff = (now - last_time).total_seconds()
            print(f"Last RPS entry was {time_diff:.2f} seconds ago.")
            print(f"Current time is {now.isoformat()} and last entry time is {last_time.isoformat()}.")

            wait_time = 40-time_diff if time_diff < 40 else 0
            print(f"⏳ Waiting {wait_time:.2f}s for fresh data...")
            time.sleep(wait_time)

        # Convert to NumPy array
        rps_series = np.array(rps_history, dtype=np.float64)

        # Train ARIMA
        model = ARIMA(rps_series, order=(2, 1, 1))
        arima_model = model.fit()
        print(f"✅ ARIMA model trained at {datetime.now(timezone.utc).isoformat()}.")

    except Exception as e:
        print(f"❌ Failed to train ARIMA model: {e}")


# Uses the trained ARIMA model to forecast the next RPS value.
def predict_next_rps():
    global arima_model
    if arima_model is None:
        print("⚠️ ARIMA model not trained. Returning fallback value.")
        return 1000
    try:
        forecast = arima_model.forecast(steps=1)
        return int(max(0, round(forecast[0])))  # Ensure RPS is non-negative
    except Exception as e:
        print(f"❌ Prediction failed: {e}")
        return 1000

if __name__ == "__main__":
    # Example usage
    train_arima_model()
    next_rps = predict_next_rps()
    print(f"Predicted next RPS: {next_rps}")
    
    # Continuously predict every minute
    while True:
        time.sleep(60)  # Wait for 1 minute
        next_rps = predict_next_rps()
        print(f"Predicted next RPS: {next_rps}")