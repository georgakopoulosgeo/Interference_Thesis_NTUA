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
    docker run --name=cadvisor -d \
      --volume=/:/rootfs:ro \
      --volume=/var/run:/var/run:rw \
      --volume=/sys:/sys:ro \
      --volume=/var/lib/docker/:/var/lib/docker:ro \
      -p 8080:8080 \
      google/cadvisor:latest

    echo "Waiting 5 seconds for cAdvisor to initialize..."
    sleep 5

    echo "Starting Prometheus container..."
    docker run --name=prometheus -d \
      -p 9090:9090 \
      -v /home/youruser/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml \
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
