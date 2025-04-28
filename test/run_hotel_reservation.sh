#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 5 ]; then
  echo "Usage: $0 THREADS CONNECTIONS DURATION REQUESTS_PER_SEC SCRIPT"
  exit 1
fi

THREADS=$1
CONNECTIONS=$2
DURATION=$3
REQUESTS_PER_SEC=$4
SCRIPT=$5

# Change these paths if your layout differs
HOTEL_RESERVATION_DIR="/home/george/Workspace/Interference/workloads/hotelReservation"
WRK2_DIR="/home/george/Workspace/Interference/wrk2"
TARGET_URL="http://127.0.0.1:5000"

echo "Setting up and running workload generator..."

# Enable port forwarding for the hotelReservation service


# Initialize any git submodules in the workload directory (if needed)
cd "$HOTEL_RESERVATION_DIR" || exit
git submodule update --init --recursive

# Build wrk2
cd "$WRK2_DIR" || exit
make

# Run wrk2 against the hotelReservation service
cd "$HOTEL_RESERVATION_DIR" || exit
"$WRK2_DIR/wrk" -D exp \
    -t "$THREADS" \
    -c "$CONNECTIONS" \
    -d "$DURATION" \
    -L \
    -s "$SCRIPT" \
    "$TARGET_URL" \
    -R "$REQUESTS_PER_SEC"

# Usage: 
# ./run_hotel_reservation.sh 2 100 60s 1000 ../wrk2/scripts/hotel-reservation/mixed-workload_type_1.lua
