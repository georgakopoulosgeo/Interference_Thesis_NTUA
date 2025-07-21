#!/bin/bash

# === USAGE CHECK ===
if [ -z "$1" ]; then
  echo "Usage: ./copy_and_generate.sh <filename>"
  exit 1
fi

FILENAME="$1"
SOURCE_DIR="/home/george/logs/traffic_generator"
DEST_DIR="/home/george/logs/naive"

# === COPY SCHEDULE FILE ===
cp "$SOURCE_DIR/rps_schedule.json" "$DEST_DIR/schedule_${FILENAME}.jsonl"

# === OVERWRITE rps_schedule.jsonl WITH HELP FILE CONTENT ===
cat "$SOURCE_DIR/rps_help_wide.txt" > "$SOURCE_DIR/rps_schedule.jsonl"

echo "Done. Schedule copied and help content written."
