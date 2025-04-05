#!/bin/bash
# manage_monitoring.sh
# This script manages the monitoring containers for the DeathStarBench experiment.
# Usage: ./manage_monitoring.sh {start|stop|remove}

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 {start|stop|remove}"
    exit 1
fi

case "$1" in
  start)
    echo "Starting cAdvisor container..."
    VERSION=v0.49.1 # use the latest release version from https://github.com/google/cadvisor/releases
    docker run -d \
    --volume=/:/rootfs:ro \
    --volume=/var/run:/var/run:ro \
    --volume=/sys:/sys:ro \
    --volume=/var/lib/docker/:/var/lib/docker:ro \
    --volume=/dev/disk/:/dev/disk:ro \
    --publish=8085:8080 \
    --name=cadvisor \
    --privileged \
    --device=/dev/kmsg \
    gcr.io/cadvisor/cadvisor:$VERSION

    #Ports:
    # 8080: Inside the container
    # 8085: Host machine

    echo "Waiting 5 seconds for cAdvisor to initialize..."
    sleep 5

    echo "Starting Prometheus container..."
    docker run --network host --name=prometheus -d \
      -p 9090:9090 \
      -v /home/ubuntu/Workspace/prometheus.yml:/etc/prometheus/prometheus.yml \
      prom/prometheus:latest
    ;;

  stop)
    echo "Stopping Prometheus container..."
    docker stop prometheus
    echo "Stopping cAdvisor container..."
    docker stop cadvisor
    ;;

  remove)
    echo "Removing Prometheus container..."
    docker rm prometheus
    echo "Removing cAdvisor container..."
    docker rm cadvisor
    ;;

  *)
    echo "Usage: $0 {start|stop|remove}"
    exit 1
    ;;
esac
