from flask import Flask
import os
import pickle

app = Flask(__name__)

# Load the model at startup
MODEL_PATH = '/model/slowdown_predictor.pkl'

try:
    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
    model_loaded = True
except Exception as e:
    model_loaded = False
    print(f"Error loading model: {e}")

@app.route('/health')
def health():
    if model_loaded:
        return {"status": "healthy", "model": "loaded"}, 200
    else:
        return {"status": "unhealthy", "model": "not loaded"}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)