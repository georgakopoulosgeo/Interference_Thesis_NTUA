#!/bin/bash
set -e  # Exit on error

# === Config ===
VERSION="01"  # ← Change version here
INTERFERENCE_TYPES=("mixed" "membw")

for interference in "${INTERFERENCE_TYPES[@]}"; do
    echo ">>> Starting test for interference type: $interference (version $VERSION)"

    # Step 1: Run controller
    cd /home/george/Workspace/Interference/naive_testing
    echo "Running naive_controller..."
    taskset -c 7 python3 naive_controller.py "${interference}_naive_v${VERSION}"

    echo "Controller started for $interference. Waiting for 5 seconds..."
    sleep 5  # Wait for the controller to start

    # Step 2: Run experiment
    cd /home/george/Workspace/Interference
    echo "Running experiment script..."
    ./run_experiment.sh "naive_v${VERSION}" wide "$interference"

    # Step 3: Reset RPS schedule file
    cd /home/george/logs/traffic_generator
    echo "Resetting RPS schedule log..."
    cat rps_help_wide.txt > rps_schedule.jsonl

    echo ">>> Finished: $interference"
    echo "============================================="
done

echo "✅ All naive experiments completed."
