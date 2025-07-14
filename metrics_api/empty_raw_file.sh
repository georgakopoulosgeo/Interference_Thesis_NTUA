#!/bin/bash

# Check if the file exists
FILE="/opt/pcm_metrics/raw_metrics.csv"

if [ -f "$FILE" ]; then
    # Empty the file contents
    > "$FILE"
    echo "Contents of $FILE have been emptied."
else
    echo "File $FILE does not exist."
fi
