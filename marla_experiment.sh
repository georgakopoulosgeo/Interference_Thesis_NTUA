#!/bin/bash
set -e  # Exit on error

# === Config ===
VERSION="04"  # ← Change version here
INTERFERENCE_TYPES=("mixed" "l3")  # Fix typo: array should be two strings

# === Handle Ctrl+C ===
cleanup() {
    echo ""
    echo "⚠️ Caught Ctrl+C! Cleaning up..."

    # Kill background jobs if they exist
    [[ -n "$controller_pid" ]] && kill "$controller_pid" 2>/dev/null || true
    [[ -n "$experiment_pid" ]] && kill "$experiment_pid" 2>/dev/null || true

    echo "🔚 Exiting early due to interruption."
    exit 1
}
trap cleanup SIGINT

for interference in "${INTERFERENCE_TYPES[@]}"; do
    echo ">>> Starting test for interference type: $interference (version $VERSION)"

    # Step 0: Reset RPS schedule file
    cd /home/george/logs/traffic_generator
    echo "Resetting RPS schedule log..."
    cat rps_help_wide.txt > rps_schedule.jsonl

    # Step 1: Run controller
    cd /home/george/Workspace/Interference/Marla
    echo "Running marla_controller..."
    taskset -c 7 python3 controller.py "${interference}_marla_v${VERSION}" &
    controller_pid=$!

    echo "Controller started for $interference. Waiting for 5 seconds..."
    sleep 5  # Wait for the controller to start

    # Step 2: Run experiment
    cd /home/george/Workspace/Interference
    echo "Running experiment script..."
    ./run_experiment.sh "marla_v${VERSION}" wide "$interference" &
    experiment_pid=$!

    # Wait for both to finish
    wait $controller_pid
    wait $experiment_pid

    echo ">>> Finished: $interference"
    echo "============================================="

    # Clear background job tracking
    unset controller_pid
    unset experiment_pid
done

echo "✅ All marla experiments completed."
