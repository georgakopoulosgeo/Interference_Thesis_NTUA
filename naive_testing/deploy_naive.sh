#!/bin/bash
# deploy_naive.sh

set -e

echo "Deleting MARLA-related deployments..."
kubectl delete deployment --ignore-not-found=true nginx-marla nginx-minikube nginx-minikube-m02

echo "Applying baseline naive deployment..."
kubectl apply -f baseline-nginx.yaml

echo "Naive deployment is live."
