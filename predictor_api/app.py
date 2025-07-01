# app.py
from flask import Flask, request, jsonify
import joblib
import numpy as np
import os

# Load model at startup
MODEL_PATH = os.path.join("models", "slowdown_predictor.pkl")
model = joblib.load(MODEL_PATH)

app = Flask(__name__)

@app.route('/')
def index():
    return "📡 Predictor API is running."

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        
        if "metrics" not in data or "replicas" not in data or "rps" not in data:
            return jsonify({"error": "Missing required fields: metrics, replicas, rps"}), 400

        # Prepare input
        metrics = data["metrics"]
        replicas = data["replicas"]
        rps = data["rps"]

        if not isinstance(metrics, list) or not isinstance(replicas, int) or not isinstance(rps, int):
            return jsonify({"error": "Incorrect types. Expected list + int + int"}), 400

        input_vector = metrics + [rps, replicas]
        input_array = np.array(input_vector).reshape(1, -1)

        # Predict
        predicted = model.predict(input_array)[0]

        return jsonify({"slowdown": round(float(predicted), 4)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
