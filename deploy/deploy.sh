#!/usr/bin/env bash
# Deploy script executed on the target VPS by the GitHub Actions deploy workflow.
# Requires: docker, docker compose v2, git.
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/chatbotrag}"
IMAGE_NAMESPACE="${IMAGE_NAMESPACE:-vietaimem}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

echo "==> Deploying ChatbotRAG (${IMAGE_TAG}) to ${APP_DIR}"

mkdir -p "$APP_DIR"
cd "$APP_DIR"

# Clone or update the repository so compose files are current.
if [ ! -d "$APP_DIR/.git" ]; then
  git clone --depth 1 --branch main https://github.com/VietAIMEM/ChatbotRAG.git "$APP_DIR"
else
  git fetch origin
  git reset --hard origin/main
fi

# If no .env exists yet, bootstrap it from the example.
if [ ! -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  echo "==> Created .env from .env.example. Edit it before the first real run."
fi

export IMAGE_NAMESPACE
export IMAGE_TAG

echo "==> Pulling images"
docker compose pull

echo "==> Starting stack"
docker compose up -d --remove-orphans

echo "==> Pruning old images"
docker image prune -f

echo "==> Done"
