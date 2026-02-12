"""Unit tests for SSVNs (^$JOB, ^$ROUTINE, ^$SYSTEM).

Spec 021 Phase 13 (T083-T085): Tests for structured system variable handlers.
"""

import os

import pytest
from m2py.runtime.globals import InMemoryGlobalStorage


@pytest.mark.codegen
class TestSsvnJob:
    """Tests for ^$JOB SSVN — process liveness check."""

    def test_current_process_exists(self):
        """^$JOB($J) returns '1' for current process."""
        storage = InMemoryGlobalStorage()
        pid = str(os.getpid())
        result = storage.ssvn_job(pid)
        assert result == "1"

    def test_nonexistent_pid_returns_empty(self):
        """^$JOB(99999999) returns '' for nonexistent PID."""
        storage = InMemoryGlobalStorage()
        result = storage.ssvn_job("99999999")
        assert result == ""

    def test_zero_pid_returns_empty(self):
        """^$JOB(0) returns '' — PID 0 is not a user process."""
        storage = InMemoryGlobalStorage()
        result = storage.ssvn_job("0")
        assert result == ""

    def test_negative_pid_returns_empty(self):
        """^$JOB(-1) returns '' — invalid PID."""
        storage = InMemoryGlobalStorage()
        result = storage.ssvn_job("-1")
        assert result == ""

    def test_non_numeric_pid_returns_empty(self):
        """^$JOB("abc") returns '' — non-numeric PID."""
        storage = InMemoryGlobalStorage()
        result = storage.ssvn_job("abc")
        assert result == ""


@pytest.mark.codegen
class TestSsvnRoutine:
    """Tests for ^$ROUTINE SSVN — routine existence check."""

    def test_existing_routine_returns_empty(self):
        """^$ROUTINE returns '' — no routine metadata in memory backend."""
        storage = InMemoryGlobalStorage()
        result = storage.ssvn_routine("TEST")
        assert result == ""


@pytest.mark.codegen
class TestSsvnSystem:
    """Tests for ^$SYSTEM SSVN."""

    def test_system_returns_m2py(self):
        """^$SYSTEM codegen delegates to _rt.system()."""
        from m2py.codegen import generate_python

        code = "TEST W ^$SYSTEM,! Q\n"
        result = generate_python(code)
        assert "_rt.system()" in result

    def test_system_with_subscript(self):
        """^$SYSTEM with subscript also generates code."""
        from m2py.codegen import generate_python

        code = 'TEST S X=^$S("VERSION") W X,! Q\n'
        result = generate_python(code)
        assert "_rt.system()" in result or "ssvn" in result.lower()


@pytest.mark.codegen
class TestSsvnGlobal:
    """Tests for ^$GLOBAL SSVN — global existence check."""

    def test_existing_global_returns_one(self):
        """^$GLOBAL returns '1' for existing global."""
        storage = InMemoryGlobalStorage()
        storage.set("TEST", [], "value")
        result = storage.ssvn_global("TEST")
        assert result == "1"

    def test_nonexistent_global_returns_empty(self):
        """^$GLOBAL returns '' for nonexistent global."""
        storage = InMemoryGlobalStorage()
        result = storage.ssvn_global("NONEXIST")
        assert result == ""


@pytest.mark.codegen
class TestSsvnLock:
    """Tests for ^$LOCK SSVN — lock status check."""

    def test_locked_returns_count(self):
        """^$LOCK returns lock count for locked name."""
        storage = InMemoryGlobalStorage()
        storage.lock("TESTLOCK", (), lock_type="+")
        result = storage.ssvn_lock("TESTLOCK")
        assert result == "1"

    def test_unlocked_returns_empty(self):
        """^$LOCK returns '' for unlocked name."""
        storage = InMemoryGlobalStorage()
        result = storage.ssvn_lock("TESTLOCK")
        assert result == ""
