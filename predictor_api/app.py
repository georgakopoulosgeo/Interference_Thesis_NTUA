from flask import Flask, request, jsonify
import joblib
import numpy as np
import os

app = Flask(__name__)

# Load models at startup
MODELS_DIR = "models" # Directory where models are stored // Needs Change!
models = {}

try:
    for replicas in [1, 2, 3, 4]:
        filename = os.path.join(MODELS_DIR, f"model_replicas_{replicas}.pkl")
        models[replicas] = joblib.load(filename)
    print("All models loaded successfully!")
except Exception as e:
    print(f"Error loading models: {str(e)}")
    raise

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        
        # Validate input
        if not all(k in data for k in ["node_metrics", "replicas"]):
            return jsonify({"error": "Missing required fields"}), 400
            
        replicas = data["replicas"]
        if replicas not in models:
            return jsonify({"error": f"Unsupported replica count: {replicas}"}), 400
            
        # Convert to numpy array and ensure correct shape
        features = np.array(data["node_metrics"]).reshape(1, -1)
        
        # Predict
        slowdown = models[replicas].predict(features)[0]
        return jsonify({
            "replicas": replicas,
            "slowdown": float(slowdown),  # Convert numpy float to native float
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)