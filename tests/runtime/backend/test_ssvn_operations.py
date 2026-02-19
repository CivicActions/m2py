"""Tests for Structured System Variable Name (SSVN) operations.

Validates ^$GLOBAL, ^$JOB, ^$LOCK, and ^$ROUTINE system variable access
across all backends (inmemory, yottadb, iris).

MUMPS SSVNs provide introspection into the runtime environment:
  ^$GLOBAL(name)     - Whether a global exists
  ^$JOB(pid)         - Whether a process is alive
  ^$LOCK(name)       - Lock count on a resource
  ^$ROUTINE(name)    - Whether a routine is available
"""

from __future__ import annotations

import os

import pytest

from m2py.runtime.globals import GlobalStorageBackend


# =============================================================================
# ^$GLOBAL - Global existence queries
# =============================================================================


class TestSSVNGlobal:
    """Tests for ssvn_global() - ^$GLOBAL(name) queries."""

    def test_nonexistent_global_returns_empty(self, backend: GlobalStorageBackend):
        """^$GLOBAL for a global that doesn't exist returns empty string."""
        result = backend.ssvn_global("DOESNOTEXIST")
        assert result == ""

    def test_existing_global_returns_truthy(self, backend: GlobalStorageBackend):
        """^$GLOBAL for a global that exists returns non-empty string."""
        backend.set("TESTGLOB", ("1",), "value")
        result = backend.ssvn_global("TESTGLOB")
        assert result != "", "Expected non-empty string for existing global"
        assert result == "1"

    def test_global_after_kill_returns_empty(self, backend: GlobalStorageBackend):
        """^$GLOBAL returns empty after the global is killed."""
        backend.set("KILLME", ("a",), "val")
        assert backend.ssvn_global("KILLME") == "1"
        backend.kill("KILLME", ())
        assert backend.ssvn_global("KILLME") == ""

    def test_global_with_only_descendant_nodes(self, backend: GlobalStorageBackend):
        """^$GLOBAL returns truthy when global has subscripted data only."""
        backend.set("SUBONLY", ("1", "2"), "deep")
        result = backend.ssvn_global("SUBONLY")
        assert result != "", "Global with descendant nodes should exist"

    def test_multiple_globals_independent(self, backend: GlobalStorageBackend):
        """Each global is independently queryable."""
        backend.set("FIRST", ("1",), "a")
        backend.set("SECOND", ("1",), "b")
        assert backend.ssvn_global("FIRST") == "1"
        assert backend.ssvn_global("SECOND") == "1"
        assert backend.ssvn_global("THIRD") == ""


# =============================================================================
# ^$JOB - Process existence queries
# =============================================================================


class TestSSVNJob:
    """Tests for ssvn_job() - ^$JOB(pid) queries."""

    def test_current_process_exists(self, backend: GlobalStorageBackend):
        """^$JOB for the current process PID returns truthy."""
        pid = str(os.getpid())
        result = backend.ssvn_job(pid)
        assert result != "", f"Current process PID {pid} should exist"
        assert result == "1"

    def test_nonexistent_pid_returns_empty(self, backend: GlobalStorageBackend):
        """^$JOB for a PID that doesn't exist returns empty string."""
        # Use a very high PID unlikely to exist
        result = backend.ssvn_job("4999999")
        assert result == ""

    def test_invalid_pid_returns_empty(self, backend: GlobalStorageBackend):
        """^$JOB for a non-numeric value returns empty string."""
        assert backend.ssvn_job("notapid") == ""
        assert backend.ssvn_job("") == ""

    def test_negative_pid_returns_empty(self, backend: GlobalStorageBackend):
        """^$JOB for a negative PID returns empty string."""
        result = backend.ssvn_job("-1")
        assert result == ""

    def test_zero_pid_returns_empty(self, backend: GlobalStorageBackend):
        """^$JOB for PID 0 returns empty string."""
        result = backend.ssvn_job("0")
        assert result == ""

    def test_pid_1_exists(self, backend: GlobalStorageBackend):
        """^$JOB for PID 1 (init) should return truthy on Linux."""
        result = backend.ssvn_job("1")
        # PID 1 always exists on Linux (init/systemd)
        assert result == "1"


# =============================================================================
# ^$LOCK - Lock state queries
# =============================================================================


class TestSSVNLock:
    """Tests for ssvn_lock() - ^$LOCK(name) queries."""

    def test_unlocked_resource_returns_empty(self, backend: GlobalStorageBackend):
        """^$LOCK for an unlocked resource returns empty string."""
        result = backend.ssvn_lock("NOLOCKHERE")
        assert result == ""

    def test_locked_resource_returns_count(self, backend: GlobalStorageBackend):
        """^$LOCK for a locked resource returns the lock count."""
        backend.lock("LOCKTEST", (), timeout=5)
        result = backend.ssvn_lock("LOCKTEST")
        assert result != "", "Locked resource should have non-empty lock info"
        # Lock count should be at least 1
        assert int(result) >= 1
        backend.unlock("LOCKTEST", ())

    def test_lock_count_after_unlock(self, backend: GlobalStorageBackend):
        """^$LOCK returns empty after resource is unlocked."""
        backend.lock("UNLOCKTEST", (), timeout=5)
        assert backend.ssvn_lock("UNLOCKTEST") != ""
        backend.unlock("UNLOCKTEST", ())
        result = backend.ssvn_lock("UNLOCKTEST")
        assert result == "", "Unlocked resource should return empty"

    def test_nested_lock_count(self, backend: GlobalStorageBackend, backend_name: str):
        """^$LOCK reflects incremented count for nested locks."""
        if backend_name == "iris":
            pytest.skip("IRIS lock counting differs for incremental locks")
        backend.lock("NESTED", (), timeout=5)
        backend.lock("NESTED", (), timeout=5)
        result = backend.ssvn_lock("NESTED")
        assert int(result) == 2, f"Expected lock count 2, got {result}"
        backend.unlock("NESTED", ())
        result = backend.ssvn_lock("NESTED")
        assert int(result) == 1, f"Expected lock count 1 after one unlock, got {result}"
        backend.unlock("NESTED", ())

    def test_unlock_all_clears_lock_state(self, backend: GlobalStorageBackend):
        """^$LOCK returns empty for all resources after unlock_all()."""
        backend.lock("CLEARME1", (), timeout=5)
        backend.lock("CLEARME2", (), timeout=5)
        backend.unlock_all()
        assert backend.ssvn_lock("CLEARME1") == ""
        assert backend.ssvn_lock("CLEARME2") == ""


# =============================================================================
# ^$ROUTINE - Routine metadata queries
# =============================================================================


class TestSSVNRoutine:
    """Tests for ssvn_routine() - ^$ROUTINE(name) queries."""

    def test_nonexistent_routine_returns_empty(self, backend: GlobalStorageBackend):
        """^$ROUTINE for a routine that doesn't exist returns empty string."""
        result = backend.ssvn_routine("NONEXISTENTROUTINE")
        assert result == ""

    def test_empty_name_returns_empty(self, backend: GlobalStorageBackend):
        """^$ROUTINE for empty string returns empty."""
        result = backend.ssvn_routine("")
        assert result == ""
