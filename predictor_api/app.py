from flask import Flask, request, jsonify
import os
import pickle
import requests
import pandas as pd
from typing import Dict, List

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

# Configuration
METRICS_SERVICE_URL = "http://metrics-collector:8000/metrics"
REQUEST_TIMEOUT = 5  # seconds

@app.route('/health')
def health():
    if model_loaded:
        return {"status": "healthy", "model": "loaded"}, 200
    else:
        return {"status": "unhealthy", "model": "not loaded"}, 500

# Add this to your health check
@app.route('/model_info')
def model_info():
    if not model_loaded:
        return {"error": "Model not loaded"}, 500
    
    return {
        "n_features": model.n_features_in_ if hasattr(model, 'n_features_in_') else "Unknown",
        "expected_features": len(EXPECTED_FEATURES),
        "feature_match": len(EXPECTED_FEATURES) == model.n_features_in_
    }

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
        response = requests.get(f"{METRICS_SERVICE_URL}", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        # Convert streaming CSV response to DataFrame
        csv_data = response.content.decode('utf-8')
        df = pd.read_csv(pd.compat.StringIO(csv_data))
        
        # Convert date and time to datetime if needed
        if 'System - Date' in df.columns and 'System - Time' in df.columns:
            df['timestamp'] = pd.to_datetime(
                df['System - Date'] + ' ' + df['System - Time'],
                format='%Y-%m-%d %H:%M:%S'
            )
            df.drop(['System - Date', 'System - Time'], axis=1, inplace=True)
        
        print(f"Fetched {len(df)} rows of metrics data")
        
        return df
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch metrics: {str(e)}")
    except pd.errors.EmptyDataError:
        raise Exception("No metrics data received from collector")
    except Exception as e:
        raise Exception(f"Error processing metrics data: {str(e)}")

def process_metrics_per_node(metrics_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Split metrics data per node and rename columns to match training data format
    """
    df = metrics_df.copy()
    core_to_node = {
        'Core0 (Socket-1)': ('node1', 'Core3'),
        'Core1 (Socket-1)': ('node1', 'Core4'),
        'Core2 (Socket-1)': ('node1', 'Core5'),
        'Core3 (Socket 0)': ('node2', 'Core3'),
        'Core4 (Socket 0)': ('node2', 'Core4'),
        'Core5 (Socket 0)': ('node2', 'Core5')
    }

    node_dfs = {'node1': pd.DataFrame(), 'node2': pd.DataFrame()}
    
    for core_prefix, (node_name, new_core_prefix) in core_to_node.items():
        core_cols = [col for col in df.columns if col.startswith(core_prefix)]
        system_cols = [col for col in df.columns if not any(col.startswith(f'Core{i}') for i in range(6))]
        
        node_df = df[system_cols + core_cols].copy()
        # Rename core columns to match training data format
        node_df.columns = [
            col.split('_')[-1] if not col.startswith(core_prefix) 
            else f"{new_core_prefix}_{col.split('_')[-1]}"
            for col in node_df.columns
        ]
        
        node_dfs[node_name] = pd.concat([node_dfs[node_name], node_df], ignore_index=True)
    
    # Drop unnecessary columns
    columns_to_drop = ['node_name', 'assigned_cores']
    for node_name in node_dfs:
        node_dfs[node_name] = node_dfs[node_name].drop(
            columns=[col for col in columns_to_drop if col in node_dfs[node_name].columns],
            errors='ignore'
        )
    
    # Debug print columns
    print("\nDebug: Columns in each node DataFrame:")
    for node_name, node_df in node_dfs.items():
        print(f"{node_name} columns ({len(node_df.columns)}):")
        print(sorted(node_df.columns.tolist()))
        print(f"Sample rows: {len(node_df)}\n")
    return node_dfs

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
    Calculate all required features for each node
    Returns: Dictionary of {node_name: feature_vector}
    """
    features = {}
    window_size = 2  # Adjust based on your time window needs
    
    for node_name, df in node_metrics.items():
        # Calculate AvgCore metrics (average across all cores in node)
        avg_core_metrics = {}
        core_cols = [c for c in df.columns if c.startswith('Core')]
        base_metrics = ['C0res', 'C1res', 'C6res', 'IPC', 'L2MISS', 'L3MISS', 'PhysIPC']
        
        for metric in base_metrics:
            # Calculate across all cores for this metric
            metric_cols = [c for c in core_cols if c.endswith(metric)]
            combined_series = pd.concat([df[col] for col in metric_cols], axis=0)
            
            stats = compute_windowed_stats(combined_series, window_size, ['mean', 'p95', 'std'])
            for stat, value in stats.items():
                avg_core_metrics[f'{stat}_AvgCore_{metric}'] = value
        
        # Calculate per-core metrics
        core_metrics = {}
        for core in ['Core3', 'Core4', 'Core5']:
            for metric in base_metrics:
                col_name = f"{core}_{metric}"
                if col_name in df.columns:
                    stats = compute_windowed_stats(df[col_name], window_size, ['mean', 'p95', 'std'])
                    for stat, value in stats.items():
                        core_metrics[f'{stat}_{col_name}'] = value
        
        # Combine all features in the expected order
        feature_vector = [rps, replicas]
        for feature in EXPECTED_FEATURES[2:]:  # Skip RPS and Replicas
            if feature in avg_core_metrics:
                feature_vector.append(avg_core_metrics[feature])
            elif feature in core_metrics:
                feature_vector.append(core_metrics[feature])
            else:
                feature_vector.append(0.0)  # Default value if missing
        
        features[node_name] = feature_vector
    
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
    app.run(host='0.0.0.0', port=5000)