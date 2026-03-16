"""Unit tests for _clean_munit_globals in the MUnit adapter.

Tests that MUnit transient globals are properly killed between test runs
to match real MUMPS semantics where each test invocation runs in a
separate process with a unique $J.
"""

from __future__ import annotations

import os
import sys

import pytest


@pytest.fixture
def runtime():
    """Create a minimal MUMPSRuntime for testing global cleanup."""
    from m2py.runtime import MUMPSRuntime

    rt = MUMPSRuntime()
    return rt


@pytest.fixture
def clean_munit_globals():
    """Import _clean_munit_globals from the MUnit adapter."""
    sys.path.insert(0, "tests/functional/munit")
    try:
        from lib.adapter import _clean_munit_globals

        return _clean_munit_globals
    finally:
        sys.path.pop(0)


def _populate_munit_globals(runtime, j: str) -> None:
    """Set up typical MUnit globals that persist after a test run."""
    runtime.globals.set("TMP", ("%ut", j, "UTVALS", "1"), "10")
    runtime.globals.set("TMP", ("%ut", j, "UTVALS", "2"), "5")
    runtime.globals.set("TMP", ("%ut", j, "CURR"), "1")
    runtime.globals.set("TMP", ("MUNIT-%utRSLT", j, "1"), "PASS")
    runtime.globals.set("TMP", ("GUI-MUNIT", j, "1"), "data")
    runtime.globals.set("TMP", ("%utCOVCOHORT", j, "routine"), "1")
    runtime.globals.set("TMP", ("%utCOVCOHORTSAV", j, "routine"), "1")
    runtime.globals.set("TMP", ("%utCOVRESULT", j, "1"), "result")
    runtime.globals.set("TMP", ("%utCOVREPORT", j, "1"), "report")


class TestCleanMunitGlobals:
    """Tests for _clean_munit_globals()."""

    def test_kills_utvals(self, runtime, clean_munit_globals):
        """UTVALS accumulator is killed."""
        j = str(os.getpid())
        runtime.globals.set("TMP", ("%ut", j, "UTVALS", "1"), "10")
        clean_munit_globals(runtime)
        assert runtime.globals.get("TMP", ("%ut", j, "UTVALS", "1")) is None

    def test_kills_result_globals(self, runtime, clean_munit_globals):
        """MUNIT-%utRSLT and GUI-MUNIT globals are killed."""
        j = str(os.getpid())
        runtime.globals.set("TMP", ("MUNIT-%utRSLT", j, "1"), "PASS")
        runtime.globals.set("TMP", ("GUI-MUNIT", j, "1"), "data")
        clean_munit_globals(runtime)
        assert runtime.globals.get("TMP", ("MUNIT-%utRSLT", j, "1")) is None
        assert runtime.globals.get("TMP", ("GUI-MUNIT", j, "1")) is None

    def test_kills_coverage_globals(self, runtime, clean_munit_globals):
        """Coverage-related globals are killed."""
        j = str(os.getpid())
        runtime.globals.set("TMP", ("%utCOVCOHORT", j, "r1"), "1")
        runtime.globals.set("TMP", ("%utCOVCOHORTSAV", j, "r1"), "1")
        runtime.globals.set("TMP", ("%utCOVRESULT", j, "1"), "result")
        runtime.globals.set("TMP", ("%utCOVREPORT", j, "1"), "report")
        clean_munit_globals(runtime)
        assert runtime.globals.get("TMP", ("%utCOVCOHORT", j, "r1")) is None
        assert runtime.globals.get("TMP", ("%utCOVCOHORTSAV", j, "r1")) is None
        assert runtime.globals.get("TMP", ("%utCOVRESULT", j, "1")) is None
        assert runtime.globals.get("TMP", ("%utCOVREPORT", j, "1")) is None

    def test_preserves_unrelated_globals(self, runtime, clean_munit_globals):
        """Non-MUnit globals under ^TMP are preserved."""
        j = str(os.getpid())
        runtime.globals.set("TMP", ("MYAPP", j, "data"), "keep")
        runtime.globals.set("TMP", ("%ut", j, "UTVALS", "1"), "10")
        clean_munit_globals(runtime)
        assert runtime.globals.get("TMP", ("MYAPP", j, "data")) == "keep"

    def test_preserves_other_jobs(self, runtime, clean_munit_globals):
        """MUnit globals from other $J values are untouched."""
        j = str(os.getpid())
        other_j = str(int(j) + 999)
        runtime.globals.set("TMP", ("%ut", other_j, "UTVALS", "1"), "10")
        runtime.globals.set("TMP", ("%ut", j, "UTVALS", "1"), "10")
        clean_munit_globals(runtime)
        assert runtime.globals.get("TMP", ("%ut", other_j, "UTVALS", "1")) == "10"

    def test_all_globals_cleaned(self, runtime, clean_munit_globals):
        """All known MUnit globals are cleaned in a single call."""
        j = str(os.getpid())
        _populate_munit_globals(runtime, j)
        clean_munit_globals(runtime)
        # Every MUnit global should be gone
        assert runtime.globals.get("TMP", ("%ut", j, "UTVALS", "1")) is None
        assert runtime.globals.get("TMP", ("%ut", j, "CURR")) is None
        assert runtime.globals.get("TMP", ("MUNIT-%utRSLT", j, "1")) is None
        assert runtime.globals.get("TMP", ("GUI-MUNIT", j, "1")) is None
        assert runtime.globals.get("TMP", ("%utCOVCOHORT", j, "routine")) is None

    def test_idempotent(self, runtime, clean_munit_globals):
        """Calling cleanup twice doesn't raise errors."""
        j = str(os.getpid())
        runtime.globals.set("TMP", ("%ut", j, "UTVALS", "1"), "10")
        clean_munit_globals(runtime)
        clean_munit_globals(runtime)  # Should not raise

    def test_empty_runtime(self, runtime, clean_munit_globals):
        """Cleanup on empty runtime doesn't raise errors."""
        clean_munit_globals(runtime)  # Should not raise
