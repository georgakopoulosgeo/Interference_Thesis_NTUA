#!/bin/bash
set -e  # Exit on error

# === Config ===
VERSION="01"  # ← Change version here
INTERFERENCE_TYPES=("cpu2")

for interference in "${INTERFERENCE_TYPES[@]}"; do
    echo ">>> Starting test for interference type: $interference (version $VERSION)"

    # Step 0: Reset RPS schedule file
    cd /home/george/logs/traffic_generator
    echo "Resetting RPS schedule log..."
    cat rps_help_wide.txt > rps_schedule.jsonl

    # Step 1: Run controller
    cd /home/george/Workspace/Interference/naive_testing
    echo "Running naive_controller..."
    taskset -c 7 python3 naive_controller.py "${interference}_naive_v${VERSION}" &
    controller_pid=$!

    echo "Controller started for $interference. Waiting for 5 seconds..."
    sleep 5  # Wait for the controller to start

    # Step 2: Run experiment
    cd /home/george/Workspace/Interference
    echo "Running experiment script..."
    ./run_experiment.sh "naive_v${VERSION}" wide "$interference" &
    experiment_pid=$!

    # Wait for both to finish
    wait $controller_pid
    wait $experiment_pid

    echo ">>> Finished: $interference"
    echo "============================================="
done

echo "✅ All naive experiments completed."
