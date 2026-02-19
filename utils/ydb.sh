#!/usr/bin/env bash
# utils/ydb.sh — Run commands inside the m2py-ydb Docker container
#
# Mounts the workspace and runs commands with YottaDB environment configured.
# Auto-builds the Docker image on first use.
#
# Usage:
#   bash utils/ydb.sh uv run pytest tests/ -x -n0    # Run tests
#   bash utils/ydb.sh uv run python -c "import yottadb; print('ok')"
#   bash utils/ydb.sh bash                            # Interactive shell
#
# The container gets YDB env vars from ydb_env_set automatically.
# The workspace is mounted at /workspace (read-write).

set -euo pipefail

IMAGE_NAME="m2py-ydb"
DOCKERFILE="Dockerfile.yottadb"

# Find project root (directory containing this script's parent)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Auto-build image if it doesn't exist ---
if ! docker image inspect "$IMAGE_NAME" > /dev/null 2>&1; then
    echo "==> Building $IMAGE_NAME image (first time only)..."
    docker build -f "$PROJECT_ROOT/$DOCKERFILE" -t "$IMAGE_NAME" "$PROJECT_ROOT"
    echo "==> Image built successfully."
fi

# --- Run command in container ---
# If no args, default to interactive bash
if [ $# -eq 0 ]; then
    set -- bash
fi

exec docker run --rm -it \
    -v "$PROJECT_ROOT:/workspace" \
    "$IMAGE_NAME" \
    "$@"
