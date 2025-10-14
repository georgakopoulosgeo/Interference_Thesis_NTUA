#!/bin/bash
set -e

# === Config ===
TRAFFIC_GEN_DIR="/home/george/Workspace/Interference/Evaluation/traffic_generator"    # Path to traffic generator
INTERFERENCE_DIR="/home/george/Workspace/Interference/Interference_Injection"         # Path to interference injection scripts
RESULTS_DIR="/home/george/logs/traffic_generator"                                     # Where to store results / Path to host machine
TASKSET_CORE="6"
DURATION_MINUTES="30"
DURATION_SECONDS=$((DURATION_MINUTES * 60))

# === Args ===
if [ $# -ne 3 ]; then
  echo "Usage: $0 <filename> <traffic: low|wide> <interference: cpu|l3|membw|mixed>"
  exit 1
fi

TRAFFIC="${2^^}"
TRAFFIC_LIST="RPS_30MIN_GRADUAL_$TRAFFIC"
INTERFERENCE_SCHEDULE="$3"
FILENAME="$INTERFERENCE_SCHEDULE"_"$1"

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

  taskset -c "$TASKSET_CORE" python3 -u "$TRAFFIC_GEN_DIR/generator.py" "$TRAFFIC_LIST" "performance_$FILENAME" "$DURATION_MINUTES" &
  TRAFFIC_PID=$!

  taskset -c "$TASKSET_CORE" python3 -u "$INTERFERENCE_DIR/inject_ibench_pods.py" "$INTERFERENCE_SCHEDULE" "$DURATION_MINUTES" &
  INTERFERENCE_PID=$!

  wait "$TRAFFIC_PID" "$INTERFERENCE_PID"
  echo "[$(date)] Experiment completed"
} | tee -a "$LOG_FILE"
