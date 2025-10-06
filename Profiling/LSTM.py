import os
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
import joblib
from tqdm import tqdm

# Configuration
TARGET_CORES = [3, 4, 5]
WINDOW_SIZE = 40  # Your 40-row time window
METRICS = ['IPC', 'L3MISS', 'L2MISS', 'C0res%', 'C1res%', 'C6res%', 'PhysIPC', 'PhysIPC%']
DATA_DIRS = ["Memento_V01", "Memento_V02", "Memento_V03", "Memento_V04",
            "Memento_V02_3_MixedScenarios", "Memento_V01_mix_scenarios", 
            "TheGame_V01", "TheGame_V02", "TheGame_V02_2", "TheGame_V03", 
            "TheGame_V04", "TheGame_MIX_V01", "TheGame_MIX_V02",
            "Fight_Club_V01", "Fight_Club_V02", "Green_Book_V01"]

def load_raw_sequence_data(data_dirs, target_cores=TARGET_CORES, metrics=METRICS):
    """Load raw time-series data from all directories"""
    X_sequences = []
    y_values = []
    test_ids = []
    
    for data_dir in tqdm(data_dirs, desc="Processing directories"):
        # Load performance data
        perf_file = os.path.join(data_dir, 'nginx_metrics.csv')
        if not os.path.exists(perf_file):
            continue
            
        df_perf = pd.read_csv(perf_file)
        df_perf['UniqueID'] = df_perf['Test_ID'].astype(str) + "_" + data_dir
        
        # Load PCM data
        pcm_files = [f for f in os.listdir(data_dir) if f.startswith('pcm_core_') and f.endswith('.csv')]
        
        for pcm_file in pcm_files:
            test_id = pcm_file.replace('pcm_core_', '').replace('.csv', '')
            unique_id = f"{test_id}_{data_dir}"
            
            # Get corresponding performance data
            perf_data = df_perf[df_perf['UniqueID'] == unique_id]
            if perf_data.empty:
                continue
                
            norm_perf = perf_data['norm_perf'].values[0]
            
            # Load raw PCM data
            df_pcm = pd.read_csv(os.path.join(data_dir, pcm_file))
            
            # Select relevant columns
            sequence_data = []
            for core in target_cores:
                for metric in metrics:
                    col_name = f'Core{core} (Socket 0) - {metric}'
                    if col_name in df_pcm.columns:
                        sequence_data.append(df_pcm[col_name].values)
            
            # Transpose to get (timesteps, features)
            if sequence_data:
                sequence_array = np.array(sequence_data).T
                if sequence_array.shape[0] >= WINDOW_SIZE:
                    X_sequences.append(sequence_array[:WINDOW_SIZE])
                    y_values.append(norm_perf)
                    test_ids.append(unique_id)
    
    return np.array(X_sequences), np.array(y_values), test_ids

def build_lstm_model(input_shape):
    """Create LSTM model architecture"""
    model = Sequential([
        LSTM(128, input_shape=input_shape, return_sequences=True),
        Dropout(0.3),
        LSTM(64, return_sequences=False),
        Dropout(0.2),
        Dense(32, activation='relu'),
        Dense(1)  # Regression output for norm_perf
    ])
    
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return model

def preprocess_data(X, y):
    """Normalize data and split into train/test sets"""
    # Reshape for scaling (flatten timesteps)
    original_shape = X.shape
    X_flat = X.reshape(-1, original_shape[2])
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_flat).reshape(original_shape)
    
    # Scale target
    y_scaler = MinMaxScaler()
    y_scaled = y_scaler.fit_transform(y.reshape(-1, 1)).flatten()
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y_scaled, test_size=0.2, random_state=42
    )
    
    return X_train, X_test, y_train, y_test, scaler, y_scaler

def main():
    # Step 1: Load and prepare data
    print("Loading raw time-series data...")
    X, y, test_ids = load_raw_sequence_data(DATA_DIRS)
    print(f"Loaded {len(X)} sequences with shape {X.shape}")
    
    # Step 2: Preprocess data
    print("Preprocessing data...")
    X_train, X_test, y_train, y_test, feature_scaler, target_scaler = preprocess_data(X, y)
    
    # Step 3: Build and train LSTM model
    print("Building LSTM model...")
    model = build_lstm_model((WINDOW_SIZE, X_train.shape[2]))
    model.summary()
    
    print("Training model...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=50,
        batch_size=32,
        verbose=1
    )
    
    # Step 4: Save the model and scalers
    print("Saving model and scalers...")
    model.save("lstm_norm_perf_predictor.keras")
    
    # Save as pickle package
    model_package = {
        'model': model,
        'feature_scaler': feature_scaler,
        'target_scaler': target_scaler,
        'input_shape': (WINDOW_SIZE, X_train.shape[2]),
        'target_cores': TARGET_CORES,
        'metrics': METRICS
    }
    
    joblib.dump(model_package, 'lstm_norm_perf_predictor.pkl')
    print("Model saved as lstm_norm_perf_predictor.pkl")

if __name__ == "__main__":
    main()