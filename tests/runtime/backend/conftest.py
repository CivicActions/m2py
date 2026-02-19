"""Pytest fixtures for backend parameterization.

Provides a `backend` fixture that returns an appropriate GlobalStorageBackend
instance based on the M2PY_GLOBAL_BACKEND environment variable. Each test
gets a fresh backend with all globals cleaned up.

Usage:
    def test_something(backend):
        backend.set("X", ("1",), "hello")
        assert backend.get("X", ("1",)) == "hello"

Backend selection:
    M2PY_GLOBAL_BACKEND=inmemory  (default)
    M2PY_GLOBAL_BACKEND=yottadb   (requires YottaDB container via ydb.sh)
    M2PY_GLOBAL_BACKEND=iris      (requires IRIS container via iris.sh)
"""

from __future__ import annotations

import os

import pytest

from m2py.runtime import get_global_storage
from m2py.runtime.globals import GlobalStorageBackend


def _get_backend_name() -> str:
    """Get the current backend name from environment."""
    return os.environ.get("M2PY_GLOBAL_BACKEND", "inmemory").lower()


@pytest.fixture
def backend() -> GlobalStorageBackend:
    """Provide a clean GlobalStorageBackend instance for testing.

    Returns the backend selected by M2PY_GLOBAL_BACKEND env var.
    Cleans up all globals after each test.
    """
    b = get_global_storage()
    # Clean up before test
    b.kill_all()
    b.unlock_all()
    yield b
    # Clean up after test
    b.kill_all()
    b.unlock_all()


@pytest.fixture
def backend_name() -> str:
    """Return the name of the current backend being tested."""
    return _get_backend_name()


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip tests marked for backends that aren't active.

    Tests decorated with @pytest.mark.backend_yottadb will only run when
    M2PY_GLOBAL_BACKEND=yottadb, and similarly for other backends.
    """
    current = _get_backend_name()

    for item in items:
        # Check for backend-specific markers
        for marker_name in ("backend_yottadb", "backend_iris", "backend_inmemory"):
            if marker_name in item.keywords:
                required_backend = marker_name.replace("backend_", "")
                if current != required_backend:
                    item.add_marker(
                        pytest.mark.skip(
                            reason=f"Requires {required_backend} backend "
                            f"(current: {current})"
                        )
                    )
