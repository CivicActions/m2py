#!/usr/bin/env bash
# utils/iris.sh — Run commands with an IRIS Docker container available
#
# Auto-builds a custom IRIS image (from Dockerfile.iris) on first use,
# then starts a persistent container if not running, exports connection
# env vars, and runs the given command locally.
#
# Usage:
#   bash utils/iris.sh uv run pytest tests/ -x -n0
#   bash utils/iris.sh uv run python -c "import iris; print('ok')"
#   bash utils/iris.sh bash                             # Interactive shell
#
# Environment variables exported (overridable):
#   IRIS_HOST, IRIS_PORT, IRIS_NAMESPACE, IRIS_USER, IRIS_PASSWORD
#
# Container management:
#   bash utils/iris.sh --start    # Start container only (no command)
#   bash utils/iris.sh --stop     # Stop and remove the container
#   bash utils/iris.sh --status   # Show container status
#   bash utils/iris.sh --rebuild  # Force rebuild image and recreate container

set -euo pipefail

CONTAINER_NAME="m2py-iris"
IMAGE_NAME="m2py-iris-img"
DOCKERFILE="Dockerfile.iris"

# Find project root (directory containing this script's parent)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Select base Docker image based on CPU architecture
ARCH="$(uname -m)"
if [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
    BASE_IMAGE="intersystems/iris-community-arm64:latest-cd"
else
    BASE_IMAGE="intersystems/iris-community:latest-cd"
fi

# --- Connection defaults (override via env) ---
export IRIS_HOST="${IRIS_HOST:-localhost}"
export IRIS_PORT="${IRIS_PORT:-1972}"
export IRIS_NAMESPACE="${IRIS_NAMESPACE:-USER}"
export IRIS_USER="${IRIS_USER:-_SYSTEM}"
export IRIS_PASSWORD="${IRIS_PASSWORD:-SYS}"

# --- Set backend ---
export M2PY_GLOBAL_BACKEND=iris

# --- Image build helper ---
build_image() {
    if ! docker image inspect "$IMAGE_NAME" > /dev/null 2>&1; then
        echo "==> Building $IMAGE_NAME image (first time only)..."
        docker build \
            -f "$PROJECT_ROOT/$DOCKERFILE" \
            --build-arg "BASE_IMAGE=$BASE_IMAGE" \
            -t "$IMAGE_NAME" \
            "$PROJECT_ROOT"
        echo "==> Image built successfully."
    fi
}

# --- Container helpers ---
container_status() {
    local status
    status="$(docker inspect -f '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null)" || true
    if [[ "$status" == "running" ]]; then
        echo "running"
    elif [[ -n "$status" ]]; then
        echo "stopped"
    else
        echo "absent"
    fi
}

wait_for_ready() {
    local max_wait="${1:-120}"
    local elapsed=0
    echo -n "==> Waiting for IRIS to be ready"
    while (( elapsed < max_wait )); do
        if echo "H" | docker exec -i "$CONTAINER_NAME" iris session IRIS -U USER > /dev/null 2>&1; then
            echo " ready."
            return 0
        fi
        echo -n "."
        sleep 2
        (( elapsed += 2 ))
    done
    echo " TIMEOUT"
    echo "ERROR: IRIS container did not become ready within ${max_wait}s" >&2
    return 1
}

start_container() {
    local status
    status="$(container_status)"

    if [[ "$status" == "running" ]]; then
        return 0
    fi

    # Ensure the custom image is built
    build_image

    if [[ "$status" == "stopped" ]]; then
        echo "==> Starting existing IRIS container..."
        docker start "$CONTAINER_NAME" > /dev/null
    else
        echo "==> Creating IRIS container..."
        docker run -d \
            --name "$CONTAINER_NAME" \
            -p "${IRIS_PORT}:1972" \
            "$IMAGE_NAME" \
            --check-caps false > /dev/null
    fi

    wait_for_ready

    # Password and null subscripts are baked into the image via
    # Dockerfile.iris, so no runtime setup is needed.
}

stop_container() {
    echo "==> Stopping IRIS container..."
    docker rm -f "$CONTAINER_NAME" > /dev/null 2>&1 || true
    echo "==> Stopped."
}

rebuild_image() {
    echo "==> Forcing rebuild of $IMAGE_NAME..."
    stop_container
    docker rmi -f "$IMAGE_NAME" > /dev/null 2>&1 || true
    build_image
}

# --- Handle management commands ---
case "${1:-}" in
    --start)
        start_container
        exit 0
        ;;
    --stop)
        stop_container
        exit 0
        ;;
    --rebuild)
        rebuild_image
        exit 0
        ;;
    --status)
        echo "Container: $CONTAINER_NAME"
        echo "Status: $(container_status)"
        echo "Image: $IMAGE_NAME (base: $BASE_IMAGE)"
        echo "Connection: $IRIS_USER@$IRIS_HOST:$IRIS_PORT/$IRIS_NAMESPACE"
        exit 0
        ;;
esac

# --- Ensure container is running ---
start_container

# --- Run command ---
if [ $# -eq 0 ]; then
    set -- bash
fi

exec "$@"
