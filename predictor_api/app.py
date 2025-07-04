# app.py
from flask import Flask, request, jsonify
import joblib
import numpy as np
import pandas as pd
import requests
import os
from io import StringIO
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load single model at startup
MODEL_PATH = os.path.join("models", "slowdown_predictor.pkl")
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model not found at {MODEL_PATH}")
model = joblib.load(MODEL_PATH)
logger.info("Loaded slowdown predictor model")

app = Flask(__name__)

# Configuration
METRICS_COLLECTOR_URL = "http://metrics-collector:8000"
WINDOW_SIZE = 2
STATS_TO_COMPUTE = ['mean', 'std', 'p95']

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

# Node to core mapping (which cores belong to which node)
NODE_CORE_MAPPING = {
    'node1': {
        'cores': ['Core0 (Socket-1)', 'Core1 (Socket-1)', 'Core2 (Socket-1)'],
        'remap_to': ['Core3', 'Core4', 'Core5']  # Remap to what model expects
    },
    'node2': {
        'cores': ['Core3 (Socket 0)', 'Core4 (Socket 0)', 'Core5 (Socket 0)'],
        'remap_to': ['Core3', 'Core4', 'Core5']  # Already matches model
    }
}

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

def fetch_pcm_metrics():
    """Fetch PCM metrics from metrics-collector service."""
    try:
        response = requests.get(f"{METRICS_COLLECTOR_URL}/metrics", timeout=10)
        response.raise_for_status()
        
        # Parse CSV data
        csv_data = StringIO(response.text)
        df = pd.read_csv(csv_data)
        
        logger.info(f"Fetched {len(df)} PCM metric rows")
        return df
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch PCM metrics: {e}")
        raise Exception(f"Unable to fetch PCM metrics: {e}")

def process_pcm_metrics(df, node_name):
    """Process PCM metrics for specific node and remap columns to model expectations."""
    
    if node_name not in NODE_CORE_MAPPING:
        raise ValueError(f"Unknown node: {node_name}. Available: {list(NODE_CORE_MAPPING.keys())}")
    
    node_config = NODE_CORE_MAPPING[node_name]
    core_names = node_config['cores']
    remap_to = node_config['remap_to']
    
    # Find all PCM columns for this node's cores
    node_columns = []
    for core_name in core_names:
        matching_cols = [col for col in df.columns if col.startswith(core_name)]
        node_columns.extend(matching_cols)
    
    if not node_columns:
        raise ValueError(f"No PCM columns found for node {node_name}")
    
    # Extract data for this node's cores
    node_data = df[node_columns].copy()
    node_data = node_data.dropna(how='all')
    
    if len(node_data) == 0:
        raise ValueError(f"No valid PCM data for node {node_name}")
    
    # Remap column names to match model expectations
    # Example: "Core0 (Socket-1)_IPC" -> "Core3_IPC" for node1
    column_mapping = {}
    for i, (original_core, target_core) in enumerate(zip(core_names, remap_to)):
        for col in node_columns:
            if col.startswith(original_core):
                # Extract metric name (everything after the core name)
                metric_part = col.replace(original_core, '').lstrip('_')
                # Remove % symbol if present
                metric_part = metric_part.replace('%', '')
                new_col_name = f"{target_core}_{metric_part}"
                column_mapping[col] = new_col_name
    
    # Rename columns
    node_data = node_data.rename(columns=column_mapping)
    
    # Compute statistics for each renamed column
    computed_stats = {}
    
    for col in node_data.columns:
        series = node_data[col].dropna()
        
        if len(series) > 0:
            stats = compute_windowed_stats(series, WINDOW_SIZE, STATS_TO_COMPUTE)
            
            # Store stats with proper naming convention
            for stat_name, stat_value in stats.items():
                feature_name = f"{stat_name}_{col}"
                computed_stats[feature_name] = stat_value if not np.isnan(stat_value) else 0.0
    
    # Compute AvgCore stats (average across the 3 cores)
    core_metrics = ['C0res', 'C1res', 'C6res', 'IPC', 'L2MISS', 'L3MISS', 'PhysIPC']
    
    for metric in core_metrics:
        # Get columns for this metric across all 3 cores
        metric_cols = [col for col in node_data.columns if col.endswith(f'_{metric}')]
        
        if metric_cols:
            # Average across cores for each row, then compute stats
            avg_series = node_data[metric_cols].mean(axis=1).dropna()
            
            if len(avg_series) > 0:
                stats = compute_windowed_stats(avg_series, WINDOW_SIZE, STATS_TO_COMPUTE)
                
                for stat_name, stat_value in stats.items():
                    feature_name = f"{stat_name}_AvgCore_{metric}"
                    computed_stats[feature_name] = stat_value if not np.isnan(stat_value) else 0.0
    
    logger.info(f"Computed {len(computed_stats)} PCM features for node {node_name}")
    return computed_stats

def build_feature_vector(rps, replicas, pcm_stats):
    """Build feature vector in expected order."""
    feature_vector = []
    
    for feature_name in EXPECTED_FEATURES:
        if feature_name == 'RPS':
            feature_vector.append(rps)
        elif feature_name == 'Replicas_x':
            feature_vector.append(replicas)
        elif feature_name in pcm_stats:
            feature_vector.append(pcm_stats[feature_name])
        else:
            # Missing feature - use 0 as fallback
            feature_vector.append(0.0)
            logger.warning(f"Missing feature: {feature_name}, using 0.0")
    
    return feature_vector

@app.route('/')
def index():
    return "📡 SLO-Aware Predictor API is running."

@app.route('/health')
def health():
    """Health check endpoint."""
    try:
        # Quick test to fetch metrics
        df = fetch_pcm_metrics()
        return jsonify({
            "status": "healthy",
            "model_loaded": True,
            "expected_features": len(EXPECTED_FEATURES),
            "latest_metrics_count": len(df)
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        
        # Validate input
        required_fields = ["replicas", "rps", "node"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        replicas = data["replicas"]
        rps = data["rps"]
        node = data["node"]
        
        # Validate types
        if not isinstance(replicas, int) or not isinstance(rps, int) or not isinstance(node, str):
            return jsonify({"error": "Invalid types. Expected int, int, str"}), 400
        
        # Fetch and process PCM metrics
        logger.info(f"Processing prediction for node={node}, replicas={replicas}, rps={rps}")
        
        pcm_df = fetch_pcm_metrics()
        pcm_stats = process_pcm_metrics(pcm_df, node)
        
        # Build feature vector
        feature_vector = build_feature_vector(rps, replicas, pcm_stats)
        
        # Make prediction
        input_array = np.array(feature_vector).reshape(1, -1)
        predicted_slowdown = model.predict(input_array)[0]
        
        logger.info(f"Predicted slowdown: {predicted_slowdown}")
        
        return jsonify({
            "slowdown": round(float(predicted_slowdown), 4),
            "node": node,
            "replicas": replicas,
            "rps": rps,
            "features_used": len(feature_vector)
        })
    
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)