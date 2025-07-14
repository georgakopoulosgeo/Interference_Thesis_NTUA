#!/bin/bash

# Absolute or relative paths
SRC_MODEL="./models/slowdown_predictor_new.pkl"
DEST_DIR="../predictor_api"
DEST_MODEL="$DEST_DIR/slowdown_predictor_new.pkl"


# Copy the model file
if [ -f "$SRC_MODEL" ]; then
    cp "$SRC_MODEL" "$DEST_MODEL"
    echo "✅ Model copied to $DEST_MODEL"
else
    echo "❌ Source model not found: $SRC_MODEL"
    exit 1
fi
