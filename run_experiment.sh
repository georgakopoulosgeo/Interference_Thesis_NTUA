#!/bin/bash
set -e

# === Config ===
TRAFFIC_GEN_DIR="/home/george/Workspace/Interference/traffic_generator"
INTERFERENCE_DIR="/home/george/Workspace/Interference/interference_injection"
RESULTS_DIR="/home/george/logs/traffic_generator"
TASKSET_CORE="6"
DURATION_MINUTES="30"
DURATION_SECONDS=$((DURATION_MINUTES * 60))

# === Args ===
if [ $# -ne 3 ]; then
  echo "Usage: $0 <filename> <traffic: low|wide> <interference: light|ramp_up|balanced>"
  exit 1
fi

FILENAME="$1"
TRAFFIC_LIST="RPS_30MIN_GRADUAL_${2^^}"  # e.g. low → RPS_30MIN_GRADUAL_LOW
INTERFERENCE_SCHEDULE="$3"

# === Paths ===
#OUTPUT_CSV="$RESULTS_DIR/$FILENAME"
LOG_FILE="$RESULTS_DIR/experiment_$FILENAME.log"
mkdir -p "$RESULTS_DIR"

# === Cleanup on Ctrl+C ===
cleanup() {
  echo "[$(date)] Caught signal, stopping..." | tee -a "$LOG_FILE"
  kill -TERM "$TRAFFIC_PID" "$INTERFERENCE_PID" 2>/dev/null || true
  wait "$TRAFFIC_PID" "$INTERFERENCE_PID" 2>/dev/null || true
}
trap cleanup SIGINT SIGTERM EXIT

# === Log & Run ===
{
  echo "[$(date)] Starting experiment"
  echo "CSV: $FILENAME"
  echo "Traffic: $TRAFFIC_LIST"
  echo "Interference: $INTERFERENCE_SCHEDULE"
  echo "Duration: $DURATION_MINUTES min"

  taskset -c "$TASKSET_CORE" python3 -u "$TRAFFIC_GEN_DIR/generator.py" "$TRAFFIC_LIST" "$FILENAME" "$DURATION_MINUTES" &
  TRAFFIC_PID=$!

  taskset -c "$TASKSET_CORE" python3 -u "$INTERFERENCE_DIR/inject_ibench_pods.py" "$INTERFERENCE_SCHEDULE" "$DURATION_MINUTES" &
  INTERFERENCE_PID=$!

  wait "$TRAFFIC_PID" "$INTERFERENCE_PID"
  echo "[$(date)] Experiment completed"
} | tee -a "$LOG_FILE"
