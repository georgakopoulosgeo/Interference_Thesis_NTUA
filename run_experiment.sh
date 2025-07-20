#!/bin/bash
set -e  # Exit on error

# ===== CONFIG =====
TRAFFIC_GEN_DIR="/home/george/Workspace/Interference/traffic_generator"
INTERFERENCE_DIR="/home/george/Workspace/Interference/interference_injection"
RESULTS_DIR="/home/george/logs/traffic_generator"
TASKSET_CORE="6"
DURATION_MINUTES="30"
DURATION_SECONDS=$((DURATION_MINUTES * 60))

# ===== PARSE ARGS =====
if [ $# -lt 3 ]; then
  echo "Usage: ./run_experiment.sh <output_filename.csv> <traffic_type> <interference_type>"
  echo ""
  echo "Available traffic options:"
  echo "  - low     → RPS_30MIN_GRADUAL_LOW"
  echo "  - wide    → RPS_30MIN_GRADUAL_WIDE"
  echo ""
  echo "Available interference options:"
  echo "  - light"
  echo "  - ramp_up"
  echo "  - balanced"
  exit 1
fi

FILENAME="$1"
TRAFFIC_ARG="$2"
INTERFERENCE_ARG="$3"

# ===== MAP TRAFFIC OPTION =====
case "$TRAFFIC_ARG" in
  low)
    RPS_LIST="RPS_30MIN_GRADUAL_LOW"
    ;;
  wide)
    RPS_LIST="RPS_30MIN_GRADUAL_WIDE"
    ;;
  *)
    echo "[ERROR] Invalid traffic type: $TRAFFIC_ARG"
    exit 1
    ;;
esac

# ===== MAP INTERFERENCE OPTION =====
case "$INTERFERENCE_ARG" in
  light|ramp_up|balanced)
    INTERFERENCE_SCHEDULE="dynamic_${INTERFERENCE_ARG}"
    ;;
  *)
    echo "[ERROR] Invalid interference type: $INTERFERENCE_ARG"
    exit 1
    ;;
esac

# ===== PREP PATHS =====
OUTPUT_CSV="$RESULTS_DIR/$FILENAME"
LOG_FILE="$RESULTS_DIR/experiment_$FILENAME.log"
mkdir -p "$RESULTS_DIR"

# ===== CLEANUP HANDLER =====
cleanup() {
  echo "[$(date)] Caught termination signal. Stopping experiment..." | tee -a "$LOG_FILE"
  kill -TERM "$TRAFFIC_PID" "$INTERFERENCE_PID" 2>/dev/null || true
  wait "$TRAFFIC_PID" "$INTERFERENCE_PID" 2>/dev/null || true
  echo "[$(date)] Experiment stopped." | tee -a "$LOG_FILE"
  exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# ===== LOG HEADER =====
echo "[$(date)] ===== Starting New Experiment =====" | tee -a "$LOG_FILE"
echo "Output CSV Filename: $FILENAME" | tee -a "$LOG_FILE"
echo "Traffic Pattern: $RPS_LIST" | tee -a "$LOG_FILE"
echo "Interference Schedule: $INTERFERENCE_SCHEDULE" | tee -a "$LOG_FILE"
echo "Duration: $DURATION_MINUTES minutes" | tee -a "$LOG_FILE"

# ===== START TRAFFIC GENERATOR =====
echo "[$(date)] Starting Traffic Generator..." | tee -a "$LOG_FILE"
taskset -c "$TASKSET_CORE" python3 "$TRAFFIC_GEN_DIR/generator.py" "$RPS_LIST" "$FILENAME" "$DURATION_MINUTES" >> "$LOG_FILE" 2>&1 &
TRAFFIC_PID=$!

# ===== START INTERFERENCE INJECTOR =====
echo "[$(date)] Starting Interference Injector..." | tee -a "$LOG_FILE"
taskset -c "$TASKSET_CORE" python3 "$INTERFERENCE_DIR/inject_ibench_pods.py" "$INTERFERENCE_SCHEDULE" "$DURATION_MINUTES" >> "$LOG_FILE" 2>&1 &
INTERFERENCE_PID=$!

# ===== WAIT =====
echo "[$(date)] Experiment running for $DURATION_SECONDS seconds..." | tee -a "$LOG_FILE"
wait "$TRAFFIC_PID" "$INTERFERENCE_PID"
echo "[$(date)] Experiment completed successfully." | tee -a "$LOG_FILE"
