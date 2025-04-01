#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEATHSTAR_DIR="$SCRIPT_DIR/DeathStarBench"
SOCIAL_NETWORK_DIR="$DEATHSTAR_DIR/socialNetwork"
WRK2_DIR="$DEATHSTAR_DIR/wrk2"
NGINX_IP="localhost"  # Replace with actual IP if running remotely
COMPOSE_PROJECT_NAME="socialnetwork_app"

# Handle interruption (Ctrl+C)
trap "echo 'Interrupted! Cleaning up...'; stop_application; exit 1" SIGINT

# Step 1: Build Docker images
build_images() {
  echo "Building Docker images..."
  cd "$SOCIAL_NETWORK_DIR" || exit
  docker-compose build
}

# Step 2: Start the SocialNetwork application
start_application() {
  echo "Starting SocialNetwork application..."
  cd "$SOCIAL_NETWORK_DIR" || exit
  export COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME"
  docker-compose up -d
}

# Step 3: Initialize the social graph using a dataset
# Usage: ./run_social_network.sh init_graph <graph_type>
init_graph() {
  if [ $# -lt 2 ]; then
    echo "Usage: $0 init_graph <graph_type>"
    echo "Where <graph_type> is one of: socfb-Reed98, ego-twitter, soc-twitter-follows-mun"
    exit 1
  fi

  graph_type="$2"
  echo "Initializing social graph using dataset: $graph_type..."
  cd "$SOCIAL_NETWORK_DIR" || exit
  python3 scripts/init_social_graph.py --graph="$graph_type" --ip="$NGINX_IP" --port=8080
}

# Step 4: Run workload generator
run_workload() {
  THREADS=$1
  CONNECTIONS=$2
  DURATION=$3
  REQUESTS_PER_SEC=$4
  SCRIPT=$5

  echo "Setting up and running workload generator..."
  cd "$SOCIAL_NETWORK_DIR" || exit
  git submodule update --init --recursive

  cd "$WRK2_DIR" || exit
  make

  cd "$SOCIAL_NETWORK_DIR" || exit
  "$WRK2_DIR/wrk" -D exp -t "$THREADS" -c "$CONNECTIONS" -d "$DURATION" \
              -L -s "$SCRIPT" http://$NGINX_IP:8080/wrk2-api/post/compose \
              -R "$REQUESTS_PER_SEC"
}

# Step 5: Stop the SocialNetwork application (but leave containers in place)
stop_application() {
  echo "Stopping SocialNetwork application..."
  export COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME"
  docker-compose stop
}

# Step 6: Remove the SocialNetwork application containers
remove_application() {
  echo "Removing SocialNetwork application containers..."
  export COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME"
  docker-compose rm -f
}

# Main script execution
case $1 in
  build)
    build_images
    ;;
  start)
    start_application
    ;;
  init_graph)
    init_graph "$@"
    ;;
  workload)
    if [ $# -lt 6 ]; then
      echo "Usage: $0 workload <threads> <connections> <duration> <requests/sec> <script-path>"
      exit 1
    fi
    run_workload "$2" "$3" "$4" "$5" "$6"
    ;;
  stop)
    stop_application
    ;;
  remove)
    remove_application
    ;;
  *)
    echo "Usage: $0 {build|start|init_graph|workload|stop|remove}"
    exit 1
    ;;
esac

exit 0
