from flask import Flask, request, jsonify
import joblib
import pandas as pd
import numpy as np

app = Flask(__name__)

# Load the lite export
predictor_data = joblib.load('slowdown_predictor_lite.pkl')
model = predictor_data['model']
feature_columns = predictor_data['feature_columns']

@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Get and validate input
        data = request.json
        if not data or 'features' not in data:
            return jsonify({"error": "Missing features"}), 400
        
        # Convert to DataFrame with correct column order
        input_df = pd.DataFrame([data['features']])[feature_columns]
        
        # Make prediction (returns norm_perf)
        prediction = model.predict(input_df)[0]
        
        # Convert to 0-1 score (adjust based on your norm_perf range)
        # Assuming lower norm_perf is better (closer to 1.0 is no slowdown)
        score = np.clip(2 - prediction, 0, 1)  # Example conversion
        
        return jsonify({
            "score": float(score),
            "raw_prediction": float(prediction),
            "features_used": feature_columns
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)