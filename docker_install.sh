#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "docker-compose.yml not found in ${PROJECT_ROOT}." >&2
  exit 1
fi

if ! command -v docker &>/dev/null; then
  echo "Docker is required but not installed. Please install Docker first." >&2
  exit 1
fi

if docker compose version &>/dev/null; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose &>/dev/null; then
  COMPOSE_CMD=(docker-compose)
else
  echo "Docker Compose plugin or docker-compose binary is required." >&2
  exit 1
fi

if [[ -f "${PROJECT_ROOT}/.env.example" && ! -f "${PROJECT_ROOT}/.env" ]]; then
  cp "${PROJECT_ROOT}/.env.example" "${PROJECT_ROOT}/.env"
  echo "Created default .env file from .env.example. Please review and update credentials."
fi

echo "Building and starting containers defined in docker-compose.yml..."
"${COMPOSE_CMD[@]}" -f "${COMPOSE_FILE}" up -d --build

echo "Docker services are up. Use '${COMPOSE_CMD[*]} -f ${COMPOSE_FILE} logs -f' to follow logs."
