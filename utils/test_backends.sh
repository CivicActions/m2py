#!/usr/bin/env bash
# utils/test_backends.sh — Run backend tests against all three backends
#
# Usage:
#   bash utils/test_backends.sh                          # Run tests/runtime/backend/
#   bash utils/test_backends.sh tests/runtime/backend/test_basic_operations.py
#   bash utils/test_backends.sh -k "test_set_and_get"    # Pass extra pytest args
#
# Runs the given test path/args against:
#   1. InMemory/SQLite (default, no Docker)
#   2. YottaDB (via utils/ydb.sh inside Docker container)
#   3. IRIS (via utils/iris.sh with Docker container)
#
# Exit code: 0 if all pass, 1 if any fail.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default test path if none specified
if [ $# -eq 0 ]; then
    set -- tests/runtime/backend/ -x
fi

PASS=0
FAIL=0

run_backend() {
    local label="$1"
    shift
    echo ""
    echo "============================================================"
    echo "  Backend: $label"
    echo "============================================================"
    if "$@"; then
        echo "  ✓ $label PASSED"
        (( PASS++ ))
    else
        echo "  ✗ $label FAILED"
        (( FAIL++ ))
    fi
}

cd "$PROJECT_ROOT"

# 1. InMemory (default — no M2PY_GLOBAL_BACKEND set)
run_backend "inmemory" uv run pytest "$@" -n0

# 2. YottaDB (inside Docker container, ydb.sh sets M2PY_GLOBAL_BACKEND=yottadb)
run_backend "yottadb" bash utils/ydb.sh uv run pytest "$@" -n0

# 3. IRIS (iris.sh auto-starts container, sets M2PY_GLOBAL_BACKEND=iris)
run_backend "iris" bash utils/iris.sh uv run pytest "$@" -n0

echo ""
echo "============================================================"
echo "  Results: $PASS passed, $FAIL failed"
echo "============================================================"

if (( FAIL > 0 )); then
    exit 1
fi
