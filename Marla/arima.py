import json
import time
from statsmodels.tsa.arima.model import ARIMA
import numpy as np

def get_rps_history():
    """
    Probably retrieves the historical RPS data with a query to Nginx Exporter
    """
    # Get last rps from /home/george/logs/traffic_generator/rps_schedule.jsonl
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

def train_arima_model():
    """
    Trains an ARIMA model on the historical RPS data.
    Sets the global model object.
    """
    global arima_model
    rps_history = get_rps_history()

    if len(rps_history) < 10:
        print("Not enough data to train ARIMA model.")
        return

    try:
        # Convert to a NumPy array, ensure numeric type
        rps_series = np.array(rps_history, dtype=np.float64)

        # Choose simple order (p,d,q) - e.g., ARIMA(2,1,1)
        model = ARIMA(rps_series, order=(2, 1, 1))
        arima_model = model.fit()
        print("✅ ARIMA model trained.")
    except Exception as e:
        print(f"❌ Failed to train ARIMA model: {e}")

def predict_next_rps():
    """
    Uses the trained ARIMA model to forecast the next RPS value.
    Returns: int
    """
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