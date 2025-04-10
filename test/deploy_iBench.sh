#!/bin/bash
# deploy_iBench.sh: Deploy iBench CPU interference containers with a variable replica count.
# Usage: ./deploy_iBench.sh <replica_count> [duration]
# Example: ./deploy_iBench.sh 2 120

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IBENCH_DIR="$SCRIPT_DIR/iBench"

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <replica_count> [duration_in_seconds]"
  exit 1
fi

REPLICAS=$1
if [ -z "$2" ]; then
  DURATION=120  # default duration in seconds
else
  DURATION=$2
fi

echo "Deploying iBench interference containers..."
echo "Replica count: $REPLICAS"
echo "Duration per container: $DURATION seconds"

export DURATION

# Launch the interference containers using docker-compose scaling.
cd "$IBENCH_DIR" || exit
export COMPOSE_PROJECT_NAME="ibench_interference"
docker-compose up -d --scale ibench_cpu=$REPLICAS

echo "Deployment complete. To view container status, run: docker-compose ps"
