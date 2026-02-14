"""Tests for MUMPSRuntime instance isolation and single-process semantics.

Validates that separate MUMPSRuntime instances have:
- Independent $JOB, $IO, output buffers
- Independent error state ($ECODE, $ETRAP, $ZERROR)
- Shared global storage (when using same backend)
- Correct naked indicator behavior (single-process)
- Correct single-process lock semantics

These tests do NOT use start_job() — they test runtime properties
by directly constructing MUMPSRuntime instances.

Extracted from test_job_threading.py per T128.
"""

import os

import pytest

from m2py.runtime import MUMPSRuntime
from m2py.runtime.globals import InMemoryGlobalStorage


@pytest.mark.runtime
class TestRuntimeInstanceIsolation:
    """Tests for isolation between MUMPSRuntime instances."""

    def test_child_has_different_job_id(self):
        """Separate runtimes should have independent $J."""
        storage = InMemoryGlobalStorage()
        parent_rt = MUMPSRuntime(global_storage=storage)
        child_rt = MUMPSRuntime(global_storage=storage)

        parent_pid = parent_rt.job()

        # Simulate what start_job does for child
        child_rt._job_id = parent_pid + 1

        assert child_rt.job() != parent_rt.job()
        assert child_rt.job() == parent_pid + 1

    def test_child_has_independent_output(self):
        """Separate runtimes have independent WRITE output buffers."""
        storage = InMemoryGlobalStorage()
        parent_rt = MUMPSRuntime(global_storage=storage)
        child_rt = MUMPSRuntime(global_storage=storage)

        parent_rt.write("parent")
        child_rt.write("child")

        assert parent_rt.get_output() == "parent"
        assert child_rt.get_output() == "child"

    def test_child_shares_globals(self):
        """Runtimes sharing a backend see each other's globals."""
        storage = InMemoryGlobalStorage()
        parent_rt = MUMPSRuntime(global_storage=storage)
        child_rt = MUMPSRuntime(global_storage=storage)

        # Parent sets a global
        parent_rt.globals.set("TEST", (), "hello")

        # Child should see it
        assert child_rt.globals.get("TEST", ()) == "hello"

        # Child sets a global
        child_rt.globals.set("RESULT", (), "world")

        # Parent should see it
        assert parent_rt.globals.get("RESULT", ()) == "world"

    def test_child_has_independent_error_state(self):
        """Separate runtimes have independent $ECODE, $ETRAP, $ZERROR."""
        storage = InMemoryGlobalStorage()
        parent_rt = MUMPSRuntime(global_storage=storage)
        child_rt = MUMPSRuntime(global_storage=storage)

        parent_rt.set_ecode(",M6,")
        parent_rt.set_etrap("D ^ERR Q")
        parent_rt.set_zerror("test error")

        assert child_rt.ecode() == ""
        assert child_rt.etrap() == ""
        assert child_rt.zerror() == ""

    def test_child_has_independent_io(self):
        """Separate runtimes have independent $IO."""
        storage = InMemoryGlobalStorage()
        parent_rt = MUMPSRuntime(global_storage=storage)
        child_rt = MUMPSRuntime(global_storage=storage)

        assert parent_rt.io() == "0"
        assert child_rt.io() == "0"

        # They are independent: switching parent's device doesn't affect child
        from m2py.runtime.devices import PrincipalDevice

        mock_dev = PrincipalDevice(runtime=parent_rt)
        mock_dev.name = "device1"
        parent_rt._device_table["device1"] = mock_dev
        parent_rt.use_device("device1")
        assert parent_rt.io() == "device1"
        assert child_rt.io() == "0"


@pytest.mark.runtime
class TestChildPrincipalIsolation:
    """Tests for $PRINCIPAL isolation across MUMPSRuntime instances.

    When a process is JOBbed, its $PRINCIPAL and $IO should be
    different from the parent — per MUMPS spec, $PRINCIPAL is constant
    for the life of a process and equals the initial $IO.

    Fixed suite: V4PRIN (test 40746)
    """

    def test_child_has_unique_principal(self):
        """JOB'd child runtime has a different $PRINCIPAL than parent."""
        storage = InMemoryGlobalStorage()
        parent_rt = MUMPSRuntime(global_storage=storage)

        child_pid = os.getpid() + 999

        child_rt = MUMPSRuntime(global_storage=storage)
        child_rt._job_id = child_pid
        child_device = f"/dev/null/{child_pid}"
        child_rt._principal = child_device
        child_rt._current_device.name = child_device

        assert child_rt._principal != parent_rt._principal
        assert child_rt.io() != parent_rt.io()
        assert child_rt._principal == child_rt.io()
        assert f"{child_pid}" in child_rt._principal

    def test_child_principal_contains_pid(self):
        """Child's $PRINCIPAL path includes its PID for uniqueness."""
        storage = InMemoryGlobalStorage()
        MUMPSRuntime(
            global_storage=storage
        )  # parent (unused but proves shared storage)

        child_pid = 12345
        child_rt = MUMPSRuntime(global_storage=storage)
        child_rt._job_id = child_pid
        child_device = f"/dev/null/{child_pid}"
        child_rt._principal = child_device
        child_rt._current_device.name = child_device

        assert child_rt._principal == "/dev/null/12345"
        assert child_rt.io() == "/dev/null/12345"


@pytest.mark.runtime
class TestNakedIndicatorSingleProcess:
    """Tests for naked indicator in single-process InMemoryGlobalStorage.

    The naked indicator is a plain instance variable (not thread-local).
    Cross-process JOBs use SQLiteGlobalStorage with per-connection state.
    """

    def test_naked_indicator_updated_on_set(self):
        """Setting a global should update the naked indicator."""
        storage = InMemoryGlobalStorage()

        assert storage.get_naked_indicator() is None

        storage.set("A", ("1", "2", "3"), "val")
        ni = storage.get_naked_indicator()
        assert ni is not None
        assert ni[0] == "A"
        assert ni[1] == ("1", "2")  # last subscript stripped

    def test_naked_indicator_reset_on_no_subscripts(self):
        """Setting a global with no subscripts resets naked indicator."""
        storage = InMemoryGlobalStorage()

        storage.set("A", ("1",), "val")
        assert storage.get_naked_indicator() is not None

        storage.set("B", (), "val2")
        assert storage.get_naked_indicator() is None

    def test_naked_indicator_overwritten_by_subsequent_op(self):
        """Each global operation overwrites the naked indicator."""
        storage = InMemoryGlobalStorage()

        storage.set("A", ("1", "2", "3"), "val1")
        assert storage.get_naked_indicator()[0] == "A"

        storage.set("B", ("x", "y"), "val2")
        ni = storage.get_naked_indicator()
        assert ni[0] == "B"
        assert ni[1] == ("x",)


@pytest.mark.runtime
class TestLockSingleProcess:
    """Tests for LOCK single-process semantics.

    InMemoryGlobalStorage locks are now single-process (no threading).
    Cross-process lock contention is tested via SQLiteGlobalStorage.
    """

    def test_lock_increments_count(self):
        """Acquiring the same lock twice increments the count."""
        storage = InMemoryGlobalStorage()

        assert storage.lock("RESOURCE", (), lock_type="+") is True
        assert storage.lock("RESOURCE", (), lock_type="+") is True

        # Lock table should show count of 2
        entry = storage._lock_table.get(("RESOURCE", ()))
        assert entry is not None
        assert entry[1] == 2

        storage.unlock("RESOURCE", ())
        # Count should be 1 after one unlock
        entry = storage._lock_table.get(("RESOURCE", ()))
        assert entry is not None
        assert entry[1] == 1

        storage.unlock("RESOURCE", ())
        # Lock should be fully released
        assert storage._lock_table.get(("RESOURCE", ())) is None

    def test_lock_release_allows_reacquire(self):
        """Releasing a lock allows it to be reacquired."""
        storage = InMemoryGlobalStorage()

        storage.lock("RESOURCE", (), lock_type="+")
        storage.unlock("RESOURCE", ())

        # Should be able to acquire again
        got_lock = storage.lock("RESOURCE", (), timeout=1.0, lock_type="+")
        assert got_lock is True
        storage.unlock("RESOURCE", ())

    def test_unlock_all_releases_all_own_locks(self):
        """unlock_all() should release all locks held by this process."""
        storage = InMemoryGlobalStorage()

        storage.lock("LOCK_A", (), lock_type="+")
        storage.lock("LOCK_B", (), lock_type="+")
        storage.lock("LOCK_C", ("sub",), lock_type="+")

        # All three locks should be in the table
        assert len(storage._lock_table) == 3

        storage.unlock_all()

        # All locks should be released
        assert len(storage._lock_table) == 0
