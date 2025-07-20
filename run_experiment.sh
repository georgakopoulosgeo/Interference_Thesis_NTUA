#!/bin/bash
set -e  # Exit on error

# ===== CONFIG =====
TRAFFIC_GEN_DIR="/home/george/Workspace/Interference/traffic_generator"
INTERFERENCE_DIR="/home/george/Workspace/Interference/interference_injection"
RESULTS_DIR="/home/george/logs/traffic_generator"
TASKSET_CORE="6"
RPS_LIST="RPS_30MIN_GRADUAL_WIDE"
DURATION_MINUTES="30"
DURATION_SECONDS=$((DURATION_MINUTES * 60))

# ===== CHECK ARGS =====
if [ $# -lt 1 ]; then
  echo "Usage: ./run_experiment.sh <output_filename.csv>"
  echo "Available traffic options:"
  echo "  - RPS_30MIN_GRADUAL_WIDE"
  echo "  - RPS_30MIN_GRADUAL_LOW"
  echo "  - PREDEFINED_RPS_15MIN_LOW"
  echo "  - PREDEFINED_RPS_15MIN_WIDE"
  exit 1
fi

FILENAME="$1"
OUTPUT_CSV="$RESULTS_DIR/$FILENAME"
LOG_FILE="$RESULTS_DIR/experiment_$FILENAME.log"

# ===== ENSURE RESULTS DIR EXISTS =====
mkdir -p "$RESULTS_DIR"

# ===== START LOGGING =====
echo "[$(date)] ===== Starting New Experiment =====" | tee -a "$LOG_FILE"
echo "Output CSV Filename: $FILENAME" | tee -a "$LOG_FILE"
echo "Traffic Pattern: $RPS_LIST" | tee -a "$LOG_FILE"
echo "Duration: $DURATION_MINUTES minutes" | tee -a "$LOG_FILE"

# ===== START TRAFFIC GENERATOR =====
echo "[$(date)] Starting Traffic Generator..." | tee -a "$LOG_FILE"
taskset -c "$TASKSET_CORE" python3 "$TRAFFIC_GEN_DIR/generator.py" "$RPS_LIST" "$FILENAME" "$DURATION_MINUTES" >> "$LOG_FILE" 2>&1 &
TRAFFIC_PID=$!

# ===== START INTERFERENCE INJECTOR =====
echo "[$(date)] Starting Interference Injector (schedule: dynamic_high)..." | tee -a "$LOG_FILE"
taskset -c "$TASKSET_CORE" python3 "$INTERFERENCE_DIR/inject_ibench_pods.py" dynamic_high "$DURATION_MINUTES" >> "$LOG_FILE" 2>&1 &
INTERFERENCE_PID=$!

# ===== CLEANUP TRAP =====
cleanup() {
  echo "[$(date)] Stopping experiment..." | tee -a "$LOG_FILE"
  kill -TERM "$TRAFFIC_PID" "$INTERFERENCE_PID" 2>/dev/null
  wait "$TRAFFIC_PID" "$INTERFERENCE_PID"
  echo "[$(date)] Experiment stopped." | tee -a "$LOG_FILE"
}
trap cleanup EXIT TERM INT

# ===== WAIT =====
echo "[$(date)] Experiment running for $DURATION_SECONDS seconds..." | tee -a "$LOG_FILE"
wait "$TRAFFIC_PID" "$INTERFERENCE_PID"
echo "[$(date)] Experiment completed successfully." | tee -a "$LOG_FILE"
