#!/usr/bin/env bash
set -euo pipefail

# 1) cd to repo root
cd "$(dirname "$0")/../.."
ROOT_FOLDER=$(pwd)

# 2) Your Docker Hub namespace (only for tagging, not pushing)
USER="georgegeo248"
TAG="latest"

# 3) Build each service locally
for SERVICE in hotelreservation frontend geo profile rate recommendation reserve search user; do
  echo "🔨 Building local image: ${USER}/${SERVICE}:${TAG}"
  docker build \
    --platform linux/amd64 \
    -t "${USER}/${SERVICE}:${TAG}" \
    -f "${ROOT_FOLDER}/Dockerfile" \
    "${ROOT_FOLDER}"
done

echo "✅ All local images built."
