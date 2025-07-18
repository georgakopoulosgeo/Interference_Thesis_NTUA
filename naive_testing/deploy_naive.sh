#!/bin/bash
# deploy_naive.sh

set -e

echo "Deleting MARLA-related deployments..."
kubectl delete deployment --ignore-not-found=true nginx-marla my-nginx-minikube my-nginx-minikube-m02
kubectl delete service --ignore-not-found=true nginx-service

echo "Applying baseline naive deployment..."
kubectl apply -f baseline-nginx.yaml

echo "Naive deployment is live."
