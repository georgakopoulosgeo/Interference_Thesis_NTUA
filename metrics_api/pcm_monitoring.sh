#!/bin/bash
# Define where to store the metrics
METRICS_DIR="/home/pcm_metrics"
mkdir -p "$METRICS_DIR"
cd "$METRICS_DIR"
# Load MSR kernel module (required for Intel PCM)
sudo modprobe msr
# Start Intel PCM tool in background, logging to raw_metrics.csv
# Sample interval = 1 second, output is CSV
sudo /home/george/Workshop/pcm/build/bin/pcm 1 -r -csv=raw_metrics.csv 1>&- 2>&- &

# Maintain a 30-line buffer of latest data in buffer_metrics.csv
while true; do
    # Copy header (top 3 lines)
    head -n 3 raw_metrics.csv > buffer_metrics_temp.csv
    # Copy last 30 lines of actual data
    tail -n 40 raw_metrics.csv >> buffer_metrics_temp.csv
    # Atomically replace the old buffer
    mv buffer_metrics_temp.csv buffer_metrics.csv
    # Wait before repeating
    sleep 2
done &