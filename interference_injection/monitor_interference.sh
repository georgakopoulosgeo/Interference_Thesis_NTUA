#!/bin/bash

# === Configuration ===
PCM_DIR="/home/george/Workspace/pcm/build/bin"
OUTPUT_DIR="/home/george/interference_injection/pcm_output"
OUTPUT_CSV="${OUTPUT_DIR}/pcm_capture_$(date +%Y%m%d_%H%M%S).csv"
INTERVAL=5        # in seconds
DURATION=6000     # total duration of the test in seconds

# === Preparation ===
mkdir -p "$OUTPUT_DIR"
cd "$PCM_DIR" || { echo "PCM directory not found!"; exit 1; }

echo "🔍 Starting PCM capture for $DURATION seconds..."
echo "📄 Output: $OUTPUT_CSV"

# === Run PCM with timeout ===
sudo timeout "$DURATION" ./pcm "$INTERVAL" -csv="$OUTPUT_CSV"

echo "✅ PCM monitoring complete."
