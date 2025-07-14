#!/bin/bash

# Define file paths
RAW_METRICS="/opt/pcm_metrics/raw_metrics.csv"
BUFFER_METRICS="/opt/pcm_metrics/buffer_metrics.csv"

# Check if files exist and remove them
if [ -f "$RAW_METRICS" ]; then
    rm -f "$RAW_METRICS"
    echo "Removed $RAW_METRICS"
else
    echo "$RAW_METRICS does not exist (skipping removal)"
fi

if [ -f "$BUFFER_METRICS" ]; then
    rm -f "$BUFFER_METRICS"
    echo "Removed $BUFFER_METRICS"
else
    echo "$BUFFER_METRICS does not exist (skipping removal)"
fi

# Recreate files
touch "$RAW_METRICS" "$BUFFER_METRICS"
echo "Recreated $RAW_METRICS and $BUFFER_METRICS"

# Optional: Set permissions (adjust as needed)
chmod 644 "$RAW_METRICS" "$BUFFER_METRICS"
echo "Permissions set to 644 (read/write for owner, read for others)"