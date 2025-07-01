#!/bin/bash

# Absolute or relative paths
SRC_MODEL="./models/slowdown_predictor.pkl"
DEST_DIR="../predictor_api/models"
DEST_MODEL="$DEST_DIR/slowdown_predictor.pkl"

# Ensure destination directory exists
mkdir -p "$DEST_DIR"

# Copy the model file
if [ -f "$SRC_MODEL" ]; then
    cp "$SRC_MODEL" "$DEST_MODEL"
    echo "✅ Model copied to $DEST_MODEL"
else
    echo "❌ Source model not found: $SRC_MODEL"
    exit 1
fi
