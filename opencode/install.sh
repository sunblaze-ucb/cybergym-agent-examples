#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENCODE_VERSION="${OPENCODE_VERSION:-1.18.13}"
IMAGE_NAME="${IMAGE_NAME:-cybergym/opencode:latest}"

docker build \
    --build-arg "OPENCODE_VERSION=${OPENCODE_VERSION}" \
    --tag "${IMAGE_NAME}" \
    "${SCRIPT_DIR}"
