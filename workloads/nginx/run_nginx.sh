#!/bin/bash
# filepath: /home/george/Workshop/Interference/workloads/nginx/run_nginx.sh

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <traffic>"
    exit 1
fi

traffic=$1

case "$traffic" in
    light)
        yaml_file="wrk-job-light.yaml"
        ;;
    medium)
        yaml_file="wrk-job-medium.yaml"
        ;;
    heavy)
        yaml_file="wrk-job-heavy.yaml"
        ;;
    *)
        echo "Invalid traffic level: $traffic"
        exit 1
        ;;
esac

echo "Deploying job using $yaml_file"
kubectl apply -f $yaml_file

echo "Waiting for job pod to start..."
# This sleep may be replaced with proper readiness checks
sleep 5

echo "Retrieving logs from job..."
kubectl logs -f job/wrk-load