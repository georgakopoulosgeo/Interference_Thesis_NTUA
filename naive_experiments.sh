#!/bin/bash
set -e  # Exit on error

VERSION="32"
INTERFERENCE_TYPES=("l3_2" "membw2")

# === Handle Ctrl+C ===
cleanup() {
    echo ""
    echo "⚠️ Caught Ctrl+C! Cleaning up..."

    if [[ -n "$controller_pid" ]] && ps -p "$controller_pid" > /dev/null 2>&1; then
        echo "🛑 Stopping controller (PID $controller_pid)..."
        kill "$controller_pid"
    fi

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

    # Step 1: Start controller (manual-stop required)
    cd /home/george/Workspace/Interference/naive_testing
    echo "Running naive..."
    taskset -c 7 python3 naive_controller.py "${interference}_naive_v${VERSION}" &
    controller_pid=$!

    echo "Controller started with PID $controller_pid. Waiting 5s..."
    sleep 5

    # Step 2: Start experiment
    cd /home/george/Workspace/Interference
    echo "Running experiment script..."
    ./run_experiment.sh "naive_v${VERSION}" wide "$interference" &
    experiment_pid=$!

    # Wait for experiment to finish
    wait $experiment_pid
    echo "✅ Experiment finished for $interference"

    # Wait 10 seconds, then kill controller
    echo "🕒 Waiting 10 seconds before stopping controller..."
    sleep 10

    if ps -p "$controller_pid" > /dev/null 2>&1; then
        echo "🛑 Stopping controller (PID $controller_pid)..."
        kill "$controller_pid"
        wait $controller_pid 2>/dev/null || true
    else
        echo "⚠️ Controller already exited."
    fi

    echo "✅ Controller stopped for $interference"
    echo "============================================="

    unset controller_pid
    unset experiment_pid
done

echo "🎉 All naive experiments completed successfully."
