#!/bin/bash
set -e  # Exit on error

# ===== Config =====
TRAFFIC_GEN_DIR="/home/george/Workspace/Interference/traffic_generator"
INTERFERENCE_DIR="/home/george/Workspace/Interference/interference_injection"
OUTPUT_CSV="/home/george/experiment_results/traffic_$(date +%Y%m%d_%H%M%S).csv"
LOG_FILE="/home/george/experiment_results/experiment_$(date +%Y%m%d_%H%M%S).log"
DURATION="1800"  # 30 minutes in seconds

# ===== Core Pinning =====
TASKSET_CORE="6"

# ===== Start Traffic Generator (gradual RPS) =====
echo "[$(date)] Starting Traffic Generator (RPS_30MIN_GRADUAL_WIDE)..." | tee -a "$LOG_FILE"
taskset -c "$TASKSET_CORE" python3 "$TRAFFIC_GEN_DIR/generator.py" RPS_30MIN_GRADUAL_WIDE "$OUTPUT_CSV" "$DURATION" >> "$LOG_FILE" 2>&1 &
TRAFFIC_PID=$!

# ===== Start Interference Injector =====
echo "[$(date)] Starting Interference Injector (schedule: dynamic_high)..." | tee -a "$LOG_FILE"
taskset -c "$TASKSET_CORE" python3 "$INTERFERENCE_DIR/inject_ibench_pods.py" dynamic_high "$DURATION" >> "$LOG_FILE" 2>&1 &
INTERFERENCE_PID=$!

# ===== Cleanup Trap =====
cleanup() {
  echo "[$(date)] Stopping experiment..." | tee -a "$LOG_FILE"
  kill -TERM "$TRAFFIC_PID" "$INTERFERENCE_PID" 2>/dev/null
  wait "$TRAFFIC_PID" "$INTERFERENCE_PID"
  echo "[$(date)] Experiment stopped." | tee -a "$LOG_FILE"
}
trap cleanup EXIT TERM INT

# ===== Wait for Completion =====
echo "[$(date)] Experiment running for $DURATION seconds..." | tee -a "$LOG_FILE"
wait "$TRAFFIC_PID" "$INTERFERENCE_PID"
echo "[$(date)] Experiment completed successfully." | tee -a "$LOG_FILE"