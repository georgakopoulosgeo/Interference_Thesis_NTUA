#!/bin/bash

set -e

echo "Deleting Naive-related deployments..."
kubectl delete deployment --ignore-not-found=true nginx-naive
kubectl delete service --ignore-not-found=true nginx-service

echo "Applying baseline naive deployment..."
kubectl apply -f nginx-lb.yaml

echo "Marla deployment is live."
