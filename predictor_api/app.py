from flask import Flask, request, jsonify
import os
import pickle
import requests
import pandas as pd
from typing import Dict, List
from io import StringIO
from collections import defaultdict

import logging
import sys

# Configure basic logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Output to stdout
    ]
)

app = Flask(__name__)
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)

# Load the model at startup
MODEL_PATH = '/model/slowdown_predictor.pkl'

try:
    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
    model_loaded = True
except Exception as e:
    model_loaded = False
    print(f"Error loading model: {e}")

# Configuration
METRICS_SERVICE_URL = "http://metrics-collector:8000/metrics"
REQUEST_TIMEOUT = 5  # seconds

@app.route('/health')
def health():
    app.logger.info("Health check endpoint called")
    if model_loaded:
        return {"status": "healthy", "model": "loaded"}, 200
    else:
        return {"status": "unhealthy", "model": "not loaded"}, 500

@app.route('/model_info')
def model_info():
    if not model_loaded:
        return {"error": "Model not loaded"}, 500
    
    try:
        return {
            "status": "model loaded",
            "n_features": len(EXPECTED_FEATURES)  # Simple confirmation
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/predict', methods=['POST'])
def predict():
    """
    Endpoint that predicts slowdown per node based on:
    - replicas: Number of replicas being deployed
    - rps: Request rate (requests per second)
    """
    try:
        # 1. Get input parameters
        data = request.get_json()
        replicas = data['replicas']
        rps = data['rps']
        
        # 2. Fetch metrics from metrics collector
        metrics_data = fetch_metrics()
        
        # 3. Process metrics per node
        node_metrics = process_metrics_per_node(metrics_data)
        
        # 4. Calculate stats and create feature set
        features = calculate_features(node_metrics, replicas, rps)
        
        # 5. Make predictions
        predictions = make_predictions(features)
        
        return jsonify(predictions)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def fetch_metrics() -> pd.DataFrame:
    """
    Fetch PCM metrics from metrics collector service
    Returns: DataFrame containing all metrics
    """
    try:
        # Fetch CSV data from metrics collector
        app.logger.debug(f"Fetching metrics from {METRICS_SERVICE_URL}")
        response = requests.get(f"{METRICS_SERVICE_URL}", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        # Convert streaming CSV response to DataFrame
        csv_data = response.content.decode('utf-8')
        df = pd.read_csv(StringIO(csv_data))

        app.logger.debug(f"Fetched {len(df)} rows of metrics data")
        
        #print(f"Fetched {len(df)} rows of metrics data")
        return df
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch metrics: {str(e)}")
    except pd.errors.EmptyDataError:
        raise Exception("No metrics data received from collector")
    except Exception as e:
        raise Exception(f"Error processing metrics data: {str(e)}")

def process_metrics_per_node(metrics_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Split metrics by node and rename core columns for node1 (cores 0-2 → 3-5).
    Keep only per-core metrics and system Date/Time.
    """
    df = metrics_df.copy()
    app.logger.debug(f"Processing metrics for {len(df)} rows")

    # Mapping of core column prefixes to target node and renamed core
    core_mapping = {
        'Core0 (Socket-1)': ('node1', 'Core3'),
        'Core1 (Socket-1)': ('node1', 'Core4'),
        'Core2 (Socket-1)': ('node1', 'Core5'),
        'Core3 (Socket 0)': ('node2', 'Core3'),
        'Core4 (Socket 0)': ('node2', 'Core4'),
        'Core5 (Socket 0)': ('node2', 'Core5'),
    }

    # Always retain System Date and Time
    base_columns = ['System - Date', 'System - Time']

    # Initialize container
    node_data = {'node1': df[base_columns].copy(), 'node2': df[base_columns].copy()}

    # Loop through mapping and assign columns
    for original_prefix, (node, new_prefix) in core_mapping.items():
        core_cols = [col for col in df.columns if col.startswith(original_prefix)]
        renamed_cols = [col.replace(original_prefix, new_prefix) for col in core_cols]
        node_data[node][renamed_cols] = df[core_cols].values

    app.logger.debug(f"Processed metrics for nodes: {list(node_data.keys())}")
    # Length of each node's DataFrame
    for node, data in node_data.items():
        app.logger.debug(f"{node} has {len(data)} rows of metrics data")
        app.logger.debug(f"{node} columns: {data.head(5)}")
    return node_data


def compute_windowed_stats(series, window_size, stats):
    """Compute rolling-window-based stats for a Series."""
    results = {}
    if window_size:
        win = series.rolling(window=window_size, center=True, min_periods=1)
        if 'mean' in stats: results['mean'] = win.mean().mean()
        if 'std' in stats: results['std'] = win.std().mean()
        if 'max' in stats: results['max'] = win.max().mean()
        if 'min' in stats: results['min'] = win.min().mean()
        if 'p95' in stats: results['p95'] = win.quantile(0.95).mean()
    else:
        if 'mean' in stats: results['mean'] = series.mean()
        if 'std' in stats: results['std'] = series.std()
        if 'max' in stats: results['max'] = series.max()
        if 'min' in stats: results['min'] = series.min()
        if 'p95' in stats: results['p95'] = series.quantile(0.95)
    return results

# Expected feature order (from your model)
EXPECTED_FEATURES = [
    'RPS', 'Replicas_x', 
    'mean_AvgCore_C0res', 'mean_AvgCore_C1res', 'mean_AvgCore_C6res', 'mean_AvgCore_IPC', 
    'mean_AvgCore_L2MISS', 'mean_AvgCore_L3MISS', 'mean_AvgCore_PhysIPC', 
    'mean_Core3_C0res', 'mean_Core3_C1res', 'mean_Core3_C6res', 'mean_Core3_IPC', 
    'mean_Core3_L2MISS', 'mean_Core3_L3MISS', 'mean_Core3_PhysIPC', 
    'mean_Core4_C0res', 'mean_Core4_C1res', 'mean_Core4_C6res', 'mean_Core4_IPC', 
    'mean_Core4_L2MISS', 'mean_Core4_L3MISS', 'mean_Core4_PhysIPC', 
    'mean_Core5_C0res', 'mean_Core5_C1res', 'mean_Core5_C6res', 'mean_Core5_IPC', 
    'mean_Core5_L2MISS', 'mean_Core5_L3MISS', 'mean_Core5_PhysIPC', 
    'p95_AvgCore_C0res', 'p95_AvgCore_C1res', 'p95_AvgCore_C6res', 'p95_AvgCore_IPC', 
    'p95_AvgCore_L2MISS', 'p95_AvgCore_L3MISS', 'p95_AvgCore_PhysIPC', 
    'p95_Core3_C0res', 'p95_Core3_C1res', 'p95_Core3_C6res', 'p95_Core3_IPC', 
    'p95_Core3_L2MISS', 'p95_Core3_L3MISS', 'p95_Core3_PhysIPC', 
    'p95_Core4_C0res', 'p95_Core4_C1res', 'p95_Core4_C6res', 'p95_Core4_IPC', 
    'p95_Core4_L2MISS', 'p95_Core4_L3MISS', 'p95_Core4_PhysIPC', 
    'p95_Core5_C0res', 'p95_Core5_C1res', 'p95_Core5_C6res', 'p95_Core5_IPC', 
    'p95_Core5_L2MISS', 'p95_Core5_L3MISS', 'p95_Core5_PhysIPC', 
    'std_AvgCore_C0res', 'std_AvgCore_C1res', 'std_AvgCore_C6res', 'std_AvgCore_IPC', 
    'std_AvgCore_L2MISS', 'std_AvgCore_L3MISS', 'std_AvgCore_PhysIPC', 
    'std_Core3_C0res', 'std_Core3_C1res', 'std_Core3_C6res', 'std_Core3_IPC', 
    'std_Core3_L2MISS', 'std_Core3_L3MISS', 'std_Core3_PhysIPC', 
    'std_Core4_C0res', 'std_Core4_C1res', 'std_Core4_C6res', 'std_Core4_IPC', 
    'std_Core4_L2MISS', 'std_Core4_L3MISS', 'std_Core4_PhysIPC', 
    'std_Core5_C0res', 'std_Core5_C1res', 'std_Core5_C6res', 'std_Core5_IPC', 
    'std_Core5_L2MISS', 'std_Core5_L3MISS', 'std_Core5_PhysIPC'
]

def calculate_features(node_metrics: Dict[str, pd.DataFrame], replicas: int, rps: int) -> Dict[str, List[float]]:
    """
    Calculate features matching the training notebook's approach
    Returns: Dictionary of {node_name: feature_vector}
    """
    features = {}
    window_size = 5  # Same as training
    stats = ['mean', 'std', 'p95']  # Same as training
    target_cores = [3, 4, 5]  # Since we renamed cores 0-2 to 3-5
    
    for node_name, df in node_metrics.items():
        features_dict = defaultdict(dict)
        core_metrics_group = defaultdict(list)
        
        # Process each target core
        for core in target_cores:
            core_prefix = f'Core{core}_'
            core_cols = [col for col in df.columns if col.startswith(core_prefix)]
            
            # Filter to metrics we care about
            keep_metrics = ['IPC', 'L3MISS', 'L2MISS', 'C0res%', 'C1res%', 'C6res%', 'PhysIPC']
            core_cols = [col for col in core_cols if any(m in col for m in keep_metrics)]
            
            for col in core_cols:
                metric = col.replace(core_prefix, '').replace('%', '')
                s = df[col]
                
                # Compute statistics
                stats_results = compute_windowed_stats(s, window_size, stats)
                for stat, value in stats_results.items():
                    features_dict[f'{stat}_{core_prefix}{metric}'] = value
                
                # Store for aggregation
                core_metrics_group[metric].append(s)
        
        # Compute aggregated stats across cores
        for metric, series_list in core_metrics_group.items():
            if series_list:  # Only if we have data
                agg_series = pd.concat(series_list, axis=1).mean(axis=1)
                agg_stats = compute_windowed_stats(agg_series, window_size, stats)
                for stat, value in agg_stats.items():
                    features_dict[f'{stat}_AvgCore_{metric}'] = value
        
        # Build feature vector in expected order
        feature_vector = [rps, replicas]
        for feature in EXPECTED_FEATURES[2:]:  # Skip RPS and Replicas
            feature_vector.append(features_dict.get(feature, 0.0))
        
        features[node_name] = feature_vector
        
        app.logger.debug(f"Generated {len(feature_vector)} features for {node_name}")
    
    return features

def make_predictions(features: Dict[str, List[float]]) -> Dict[str, float]:
    """
    Make predictions using the loaded model.
    Returns: Dictionary of {node_name: prediction}
    """
    predictions = {}
    try:
        for node_name, feature_vector in features.items():
            # Ensure the feature vector is in the correct shape (2D array)
            prediction = model.predict([feature_vector])[0]
            predictions[node_name] = round(float(prediction), 4)  # Round to 4 decimal places
        
        print(f"Made predictions: {predictions}")  # Debug log
        return predictions
    
    except Exception as e:
        print(f"Prediction failed: {str(e)}")
        raise Exception(f"Prediction error: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)