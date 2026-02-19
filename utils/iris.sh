#!/usr/bin/env bash
# utils/iris.sh — Run commands with an IRIS Docker container available
#
# Auto-starts the persistent IRIS container if not running, exports
# connection env vars, then runs the given command locally.
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

set -euo pipefail

CONTAINER_NAME="m2py-iris"

# Select Docker image based on CPU architecture
ARCH="$(uname -m)"
if [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
    IMAGE="intersystems/iris-community-arm64:latest-cd"
else
    IMAGE="intersystems/iris-community:latest-cd"
fi

# --- Connection defaults (override via env) ---
export IRIS_HOST="${IRIS_HOST:-localhost}"
export IRIS_PORT="${IRIS_PORT:-1972}"
export IRIS_NAMESPACE="${IRIS_NAMESPACE:-USER}"
export IRIS_USER="${IRIS_USER:-_SYSTEM}"
export IRIS_PASSWORD="${IRIS_PASSWORD:-SYS}"

# --- Set backend ---
export M2PY_GLOBAL_BACKEND=iris

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

    if [[ "$status" == "stopped" ]]; then
        echo "==> Starting existing IRIS container..."
        docker start "$CONTAINER_NAME" > /dev/null
    else
        echo "==> Creating IRIS container (first time may pull image)..."
        docker run -d \
            --name "$CONTAINER_NAME" \
            -p "${IRIS_PORT}:1972" \
            "$IMAGE" \
            --check-caps false > /dev/null
    fi

    wait_for_ready

    # Fix password-change-required on fresh containers
    setup_password
}

setup_password() {
    # On fresh IRIS community images the default password is expired.
    # Set it to our expected value and mark it never-expiring.
    echo -e "set p(\"Password\")=\"${IRIS_PASSWORD}\"\nset p(\"PasswordNeverExpires\")=1\nset sc=##class(Security.Users).Modify(\"${IRIS_USER}\",.p)\nhalt" \
        | docker exec -i "$CONTAINER_NAME" iris session IRIS -U "%SYS" > /dev/null 2>&1 || true
}

stop_container() {
    echo "==> Stopping IRIS container..."
    docker rm -f "$CONTAINER_NAME" > /dev/null 2>&1 || true
    echo "==> Stopped."
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
    --status)
        echo "Container: $CONTAINER_NAME"
        echo "Status: $(container_status)"
        echo "Image: $IMAGE"
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
