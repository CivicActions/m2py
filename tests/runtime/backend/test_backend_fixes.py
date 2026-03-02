"""Tests for backend fixes: merge stringification, set defensiveness, kill_all, job runner.

These tests verify fixes applied across all backends during the T132-T139
implementation. Each test exercises a specific bug fix or enhancement.

Fixes covered:
- merge_tree_recursive: int/float values must be stringified before set()
- set() defensive stringification: non-string values must not crash .encode()
- _naked_indicator property: getter/setter required for codegen
- _lock_table property: required for inspection in tests
- kill_all: must enumerate ALL globals from database, not just tracked ones
- IRIS close(): must releaseAllLocks() before closing connection
"""

from __future__ import annotations

import os

import pytest

from m2py.runtime import MUMPSRuntime

# Helpers
_backend_name = os.environ.get("M2PY_GLOBAL_BACKEND", "inmemory")


class TestMergeTreeStringification:
    """Verify merge_tree handles non-string values in MArray nodes."""

    def test_merge_integer_value(self, backend):
        """MERGE with integer-valued MArray node must not crash."""
        from m2py.runtime import MArray

        src = MArray()
        src.value = 42  # int, not str
        backend.merge_tree("TST", ("A",), src)
        assert backend.get("TST", ("A",)) == "42"

    def test_merge_float_value(self, backend):
        """MERGE with float-valued MArray node must not crash."""
        from m2py.runtime import MArray

        src = MArray()
        src.value = 3.14
        backend.merge_tree("TST", ("B",), src)
        assert backend.get("TST", ("B",)) == "3.14"

    def test_merge_none_value_skipped(self, backend):
        """MERGE with None-valued MArray node only writes children."""
        from m2py.runtime import MArray

        src = MArray()
        src.value = None
        src["1"].value = "child"
        backend.merge_tree("TST", ("C",), src)
        assert backend.get("TST", ("C",)) is None
        assert backend.get("TST", ("C", "1")) == "child"

    def test_merge_tree_with_nested_int_children(self, backend):
        """MERGE preserves int-valued children across tree depth."""
        from m2py.runtime import MArray

        src = MArray()
        src.value = "root"
        src["X"].value = 100
        src["X"]["Y"].value = 200
        backend.merge_tree("TST", ("D",), src)
        assert backend.get("TST", ("D",)) == "root"
        assert backend.get("TST", ("D", "X")) == "100"
        assert backend.get("TST", ("D", "X", "Y")) == "200"


class TestSetDefensiveStringification:
    """Verify set() coerces non-string values to strings (MUMPS canonical)."""

    def test_set_integer(self, backend):
        """set() with int value should store as string."""
        backend.set("TST", ("A",), 42)
        assert backend.get("TST", ("A",)) == "42"

    def test_set_float(self, backend):
        """set() with float value should store as string."""
        backend.set("TST", ("B",), 3.14)
        assert backend.get("TST", ("B",)) == "3.14"

    def test_set_bool(self, backend):
        """set() with bool value should store as string."""
        backend.set("TST", ("C",), True)
        result = backend.get("TST", ("C",))
        assert result in ("True", "1")

    def test_set_zero(self, backend):
        """set() with zero should store as string."""
        backend.set("TST", ("D",), 0)
        assert backend.get("TST", ("D",)) == "0"

    def test_set_string_unchanged(self, backend):
        """set() with string passes through unchanged."""
        backend.set("TST", ("E",), "hello")
        assert backend.get("TST", ("E",)) == "hello"


class TestNakedIndicator:
    """Verify _naked_indicator property works on all backends."""

    def test_initial_state(self, backend):
        """Naked indicator starts as None."""
        assert backend._naked_indicator is None

    def test_setter(self, backend):
        """Naked indicator can be set explicitly."""
        backend._naked_indicator = ("GLO", ("1", "2"))
        assert backend._naked_indicator == ("GLO", ("1", "2"))

    def test_cleared_by_none(self, backend):
        """Naked indicator can be reset to None."""
        backend._naked_indicator = ("GLO", ())
        backend._naked_indicator = None
        assert backend._naked_indicator is None

    def test_set_updates_naked(self, backend):
        """set() with subscripts updates naked indicator."""
        backend.set("TST", ("X", "Y"), "val")
        ni = backend._naked_indicator
        assert ni is not None
        assert ni[0] == "TST"
        # MUMPS naked ref = all subscripts except the last one.
        # set("TST", ("X", "Y"), ...) → naked = ("TST", ("X",))
        assert "X" in ni[1]

    def test_set_no_subscripts_clears(self, backend):
        """set() with root node clears naked indicator."""
        backend.set("TST", ("X",), "val")
        backend.set("TST", (), "root")
        assert backend._naked_indicator is None


class TestLockTable:
    """Verify _lock_table property works on all backends."""

    def test_empty_initially(self, backend):
        """Lock table starts empty."""
        assert backend._lock_table == {}

    def test_after_lock(self, backend):
        """Lock shows in _lock_table after acquisition."""
        backend.lock("TST", ("1",), lock_type="+")
        lt = backend._lock_table
        assert ("TST", ("1",)) in lt

    def test_after_unlock(self, backend):
        """Lock disappears from _lock_table after release."""
        backend.lock("TST", ("1",), lock_type="+")
        backend.lock("TST", ("1",), lock_type="-")
        lt = backend._lock_table
        assert ("TST", ("1",)) not in lt

    def test_lock_table_format(self, backend):
        """_lock_table values are lock counts (int)."""
        backend.lock("TST", ("A",), lock_type="+")
        lt = backend._lock_table
        val = lt[("TST", ("A",))]
        assert isinstance(val, int)
        assert val >= 1


class TestKillAll:
    """Verify kill_all removes ALL globals, not just tracked ones."""

    def test_kill_all_basic(self, backend):
        """kill_all removes globals set in this process."""
        backend.set("TST", ("1",), "a")
        backend.set("TST2", ("2",), "b")
        backend.kill_all()
        assert backend.get("TST", ("1",)) is None
        assert backend.get("TST2", ("2",)) is None

    def test_kill_all_preserves_system_globals_on_iris(self, backend):
        """On IRIS, kill_all must not remove system globals like ^DD."""
        if _backend_name != "iris":
            pytest.skip("IRIS-specific test")
        # Check DD exists (IRIS system global)
        val = backend.get("DD", ("0",))
        backend.kill_all()
        # DD should still exist
        assert backend.get("DD", ("0",)) == val


class TestJobRunnerBackendAwareness:
    """Verify JOB runner properly detects and uses the active backend."""

    def test_backend_detection(self):
        """MUMPSRuntime creates correct backend based on env var."""
        rt = MUMPSRuntime()
        backend_type = type(rt.globals).__name__

        if _backend_name == "inmemory":
            assert backend_type == "InMemoryGlobalStorage"
        elif _backend_name == "yottadb":
            assert backend_type == "YottaDBGlobalStorage"
        elif _backend_name == "iris":
            assert backend_type == "IRISGlobalStorage"


class TestIRISConnectionLifecycle:
    """IRIS-specific: verify connection cleanup and lock release."""

    @pytest.mark.skipif(
        _backend_name != "iris", reason="IRIS-specific connection tests"
    )
    def test_close_releases_locks(self):
        """close() must call releaseAllLocks() before closing."""
        from m2py.runtime.iris_backend import IRISGlobalStorage

        storage = IRISGlobalStorage()
        storage.lock("TST", ("X",), lock_type="+")
        assert ("TST", ("X",)) in storage._lock_table
        storage.close()
        assert storage._lock_table == {}
        assert storage._conn is None

    @pytest.mark.skipif(
        _backend_name != "iris", reason="IRIS-specific connection tests"
    )
    def test_instance_tracking(self):
        """IRIS instances are tracked for fixture cleanup."""
        from m2py.runtime.iris_backend import IRISGlobalStorage

        initial_count = len(IRISGlobalStorage._all_instances)  # noqa: F841
        storage = IRISGlobalStorage()
        # Force connection
        storage._ensure_connected()
        assert storage in IRISGlobalStorage._all_instances
        storage.close()
        assert storage not in IRISGlobalStorage._all_instances

    @pytest.mark.skipif(
        _backend_name != "iris", reason="IRIS-specific connection tests"
    )
    def test_untimed_lock_nonzero_timeout(self):
        """Untimed LOCK (timeout=None) should use non-zero timeout on IRIS."""
        from m2py.runtime.iris_backend import IRISGlobalStorage

        storage = IRISGlobalStorage()
        # timeout=None means untimed MUMPS LOCK (wait indefinitely)
        result = storage.lock("TST", ("LK",), timeout=None, lock_type="+")
        assert result is True
        assert ("TST", ("LK",)) in storage._lock_table
        storage.close()
