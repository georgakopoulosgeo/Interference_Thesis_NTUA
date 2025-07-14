from flask import Flask, request, jsonify
import os
import pickle
import requests
import pandas as pd
from typing import Dict, List
from io import StringIO
from collections import defaultdict
import numpy as np
import joblib
import json
import xgboost as xgb

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
MODEL_PATH = './slowdown_predictor.pkl'

try:
    model = joblib.load(MODEL_PATH)
    model_loaded = True
except Exception as e:
    model_loaded = False
    print(f"Error loading model: {e}")

# Configuration
METRICS_SERVICE_URL = "http://localhost:30090/metrics"
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
        # 5. Make predictions using the model
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
        'Core0 (Socket 0)': ('node1', 'Core3'),
        'Core1 (Socket 0)': ('node1', 'Core4'),
        'Core2 (Socket 0)': ('node1', 'Core5'),
        'Core3 (Socket 0)': ('node2', 'Core3'),
        'Core4 (Socket 0)': ('node2', 'Core4'),
        'Core5 (Socket 0)': ('node2', 'Core5'),
    }

    # Always retain System Date and Time
    base_columns = ['Date', 'Time']

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
        #print(f"[{node}] first 6 rows:\n{data.head(6)}")  # DEBUG 
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
'mean_Core3_IPC', 'std_Core3_IPC', 'p95_Core3_IPC', 'mean_Core3_L3MISS', 'std_Core3_L3MISS', 
'p95_Core3_L3MISS', 'mean_Core3_L2MISS', 'std_Core3_L2MISS', 'p95_Core3_L2MISS', 'mean_Core3_C0res', 
'std_Core3_C0res', 'p95_Core3_C0res', 'mean_Core3_C1res', 'std_Core3_C1res', 'p95_Core3_C1res', 
'mean_Core3_C6res', 'std_Core3_C6res', 'p95_Core3_C6res', 'mean_Core3_PhysIPC', 'std_Core3_PhysIPC', 
'p95_Core3_PhysIPC', 'mean_Core4_IPC', 'std_Core4_IPC', 'p95_Core4_IPC', 'mean_Core4_L3MISS', 
'std_Core4_L3MISS', 'p95_Core4_L3MISS', 'mean_Core4_L2MISS', 'std_Core4_L2MISS', 'p95_Core4_L2MISS', 
'mean_Core4_C0res', 'std_Core4_C0res', 'p95_Core4_C0res', 'mean_Core4_C1res', 'std_Core4_C1res', 
'p95_Core4_C1res', 'mean_Core4_C6res', 'std_Core4_C6res', 'p95_Core4_C6res', 'mean_Core4_PhysIPC', 
'std_Core4_PhysIPC', 'p95_Core4_PhysIPC', 'mean_Core5_IPC', 'std_Core5_IPC', 'p95_Core5_IPC', 
'mean_Core5_L3MISS', 'std_Core5_L3MISS', 'p95_Core5_L3MISS', 'mean_Core5_L2MISS', 'std_Core5_L2MISS',
 'p95_Core5_L2MISS', 'mean_Core5_C0res', 'std_Core5_C0res', 'p95_Core5_C0res', 'mean_Core5_C1res', 
 'std_Core5_C1res', 'p95_Core5_C1res', 'mean_Core5_C6res', 'std_Core5_C6res', 'p95_Core5_C6res', 
 'mean_Core5_PhysIPC', 'std_Core5_PhysIPC', 'p95_Core5_PhysIPC', 'mean_AvgCore_IPC', 'std_AvgCore_IPC', 
 'p95_AvgCore_IPC', 'mean_AvgCore_L3MISS', 'std_AvgCore_L3MISS', 'p95_AvgCore_L3MISS', 'mean_AvgCore_L2MISS', 
 'std_AvgCore_L2MISS', 'p95_AvgCore_L2MISS', 'mean_AvgCore_C0res', 'std_AvgCore_C0res', 'p95_AvgCore_C0res', 
 'mean_AvgCore_C1res', 'std_AvgCore_C1res', 'p95_AvgCore_C1res', 'mean_AvgCore_C6res', 'std_AvgCore_C6res', 
 'p95_AvgCore_C6res', 'mean_AvgCore_PhysIPC', 'std_AvgCore_PhysIPC', 'p95_AvgCore_PhysIPC', 
 'RPS', 'Replicas_x'
]

def compute_core_features_from_df(
    df_pcm: pd.DataFrame,
    target_cores: List[int] = [3, 4, 5],
    window_size: int = 2,
    stats: List[str] = ['mean', 'p95', 'std'],
    core_prefix_template: str = "Core{core} (Socket 0) - "
) -> Dict[str, float]:
    """
    Computes per-core and AvgCore PCM stats from a single PCM DataFrame.

    Parameters:
    - df_pcm: DataFrame with time-series PCM metrics
    - target_cores: cores to analyze (default [3,4,5])
    - window_size: window for rolling stat calculation
    - stats: stats to compute (e.g., ['mean','std','p95'])
    - core_prefix_template: pattern for column prefix

    Returns:
    - Dict of {feature_name: value}
    """
    from collections import defaultdict

    features = {}
    core_metrics_group = defaultdict(list)

    # Metrics we care about
    keep_metrics = ['IPC', 'L3MISS', 'L2MISS', 'C0res%', 'C1res%', 'C6res%', 'PhysIPC']

    for core in target_cores:
        core_prefix = core_prefix_template.format(core=core)
        core_cols = [col for col in df_pcm.columns if col.startswith(core_prefix)]
        core_cols = [col for col in core_cols if any(m in col for m in keep_metrics)]

        for col in core_cols:
            metric = col.replace(core_prefix, '').replace('%', '')
            clean_name = f'Core{core}_{metric}'
            series = df_pcm[col]

            stat_values = compute_windowed_stats(series, window_size, stats)
            for stat, value in stat_values.items():
                features[f'{stat}_{clean_name}'] = value

            core_metrics_group[metric].append(series)

    # Compute aggregated AvgCore metrics
    print(f"Aggregating core metrics for: {list(core_metrics_group.keys())}")
    for metric, series_list in core_metrics_group.items():
        #continue
        if series_list:
            df_metric = pd.concat(series_list, axis=1)
            agg_series = df_metric.mean(axis=1)  # row-wise average
            agg_stats = compute_windowed_stats(agg_series, window_size, stats)
            for stat, value in agg_stats.items():
                features[f'{stat}_AvgCore_{metric}'] = value
    print(f"Computed features: {list(features.keys())}")
    return features

def calculate_features(node_metrics: Dict[str, pd.DataFrame], replicas: int, rps: int) -> Dict[str, List[float]]:
    """
    Uses the shared core feature function to generate feature vectors for each node.
    """
    features = {}
    for node_name, df in node_metrics.items():
        feature_dict = compute_core_features_from_df(
            df_pcm=df,
            target_cores=[3, 4, 5],
            window_size=2,
            stats=['mean', 'p95', 'std'],
            core_prefix_template="Core{core} - "  # matches renamed columns in predictor
        )

        # Build final feature vector using fixed feature list
        feature_dict['RPS'] = rps
        feature_dict['Replicas_x'] = replicas 
        feature_vector = [feature_dict.get(f, 0.0) for f in EXPECTED_FEATURES]
        features[node_name] = feature_vector
        app.logger.debug(f"Length of Features {len(feature_vector)}")

    return features


def make_predictions(features: Dict[str, List[float]]) -> Dict[str, float]:
    """Make predictions using the full pipeline"""
    predictions = {}
    try:
        for node_name, feature_vector in features.items():
            #app.logger.debug(f"Feature vector for {node_name}: {dict(zip(EXPECTED_FEATURES, feature_vector))}")
            # Construct a DataFrame with proper feature names
            input_df = pd.DataFrame([feature_vector], columns=EXPECTED_FEATURES)
            
            prediction = model.predict(input_df)[0]
            predictions[node_name] = float(prediction)
            
            app.logger.debug(f"{node_name} prediction: {prediction}")
        return predictions
    except Exception as e:
        app.logger.error(f"Prediction failed: {str(e)}")
        raise Exception(f"Prediction error: {str(e)}")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)