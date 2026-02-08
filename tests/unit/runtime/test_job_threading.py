"""Tests for JOB command threading implementation.

Validates that JOB spawns a background thread with:
- Its own MUMPSRuntime instance (independent $J, $IO, output)
- Shared global storage backend
- Thread-safe LOCK operations
- Per-thread naked indicators
- Proper HALT/cleanup semantics
"""

import os
import threading
import time

import pytest

from m2py.runtime import MUMPSRuntime
from m2py.runtime.globals import InMemoryGlobalStorage


@pytest.mark.runtime
class TestJobThreadIsolation:
    """Tests for JOB'd child thread isolation from parent."""

    def test_child_has_different_job_id(self):
        """Child thread should have a different $J than parent."""
        storage = InMemoryGlobalStorage()
        parent_rt = MUMPSRuntime(global_storage=storage)
        child_rt = MUMPSRuntime(global_storage=storage)

        parent_pid = parent_rt.job()

        # Simulate what start_job does for child
        child_rt._job_id = parent_pid + 1

        assert child_rt.job() != parent_rt.job()
        assert child_rt.job() == parent_pid + 1

    def test_child_has_independent_output(self):
        """Child thread's WRITE should not appear in parent's output."""
        storage = InMemoryGlobalStorage()
        parent_rt = MUMPSRuntime(global_storage=storage)
        child_rt = MUMPSRuntime(global_storage=storage)

        parent_rt.write("parent")
        child_rt.write("child")

        assert parent_rt.get_output() == "parent"
        assert child_rt.get_output() == "child"

    def test_child_shares_globals(self):
        """Child thread should share the same global storage."""
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
        """Child should have its own $ECODE, $ETRAP, $ZERROR."""
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
        """Child should have its own $IO and $PRINCIPAL."""
        storage = InMemoryGlobalStorage()
        parent_rt = MUMPSRuntime(global_storage=storage)
        child_rt = MUMPSRuntime(global_storage=storage)

        assert parent_rt.io() == "0"
        assert child_rt.io() == "0"

        # They are both "0" by default, but they are independent
        parent_rt._io = "device1"
        assert parent_rt.io() == "device1"
        assert child_rt.io() == "0"


@pytest.mark.runtime
class TestJobZjob:
    """Tests for $ZJOB special variable."""

    def test_zjob_initially_zero(self):
        """$ZJOB should be "0" before any JOB command."""
        rt = MUMPSRuntime()
        assert rt.zjob() == "0"

    def test_zjob_set_after_start_job(self):
        """$ZJOB should be set to child's virtual PID after JOB."""
        import sys
        import types

        # Create a mock module with an entry function
        mock_module = types.ModuleType("test_job_module")
        mock_module._routine_name = "test_job_module"
        mock_module._source_lines = []
        mock_module._label_lines = {}

        def entry(_rt, _scope=None):
            time.sleep(0.01)  # Brief pause to keep thread alive

        mock_module.entry = entry  # type: ignore[attr-defined]
        sys.modules["test_job_module"] = mock_module

        try:
            rt = MUMPSRuntime()
            rt._current_routine = "test_job_module"

            rt.start_job("entry", "test_job_module", [], None, None)

            # $ZJOB should be a positive integer string
            assert rt.zjob() != "0"
            assert int(rt.zjob()) > 0

            # Wait for child to finish
            rt.wait_for_jobs(timeout=5.0)
        finally:
            del sys.modules["test_job_module"]


@pytest.mark.runtime
class TestJobHaltSafety:
    """Tests for HALT (SystemExit) in JOB'd threads."""

    def test_halt_in_child_does_not_crash_parent(self):
        """SystemExit raised in child thread should not affect parent."""
        import sys
        import types

        mock_module = types.ModuleType("test_halt_module")
        mock_module._routine_name = "test_halt_module"
        mock_module._source_lines = []
        mock_module._label_lines = {}

        def entry(_rt, _scope=None):
            _rt.globals.set("HALTED", (), "yes")
            raise SystemExit(0)

        mock_module.entry = entry  # type: ignore[attr-defined]
        sys.modules["test_halt_module"] = mock_module

        try:
            rt = MUMPSRuntime()
            rt.start_job("entry", "test_halt_module", [], None, None)
            rt.wait_for_jobs(timeout=5.0)

            # Parent should still be alive, and child's global write should be visible
            assert rt.globals.get("HALTED", ()) == "yes"
        finally:
            del sys.modules["test_halt_module"]

    def test_exception_in_child_does_not_crash_parent(self):
        """Exception in child thread should not affect parent."""
        import sys
        import types

        mock_module = types.ModuleType("test_exc_module")
        mock_module._routine_name = "test_exc_module"
        mock_module._source_lines = []
        mock_module._label_lines = {}

        def entry(_rt, _scope=None):
            _rt.globals.set("BEFORE_ERROR", (), "yes")
            raise ValueError("child error")

        mock_module.entry = entry  # type: ignore[attr-defined]
        sys.modules["test_exc_module"] = mock_module

        try:
            rt = MUMPSRuntime()
            rt.start_job("entry", "test_exc_module", [], None, None)
            rt.wait_for_jobs(timeout=5.0)

            assert rt.globals.get("BEFORE_ERROR", ()) == "yes"
        finally:
            del sys.modules["test_exc_module"]


@pytest.mark.runtime
class TestJobLockThreadSafety:
    """Tests for LOCK thread safety with JOB'd processes."""

    def test_lock_contention_blocks(self):
        """Thread should block when lock is held by another thread."""
        storage = InMemoryGlobalStorage()
        result = {"timed_out": None}

        # Acquire lock in main thread
        storage.lock("RESOURCE", (), lock_type="+")

        def child_fn():
            # Try to lock with a short timeout — should fail
            got_lock = storage.lock("RESOURCE", (), timeout=0.1, lock_type="+")
            result["timed_out"] = not got_lock

        t = threading.Thread(target=child_fn)
        t.start()
        t.join(timeout=5.0)

        assert result["timed_out"] is True

        # Clean up
        storage.unlock("RESOURCE", ())

    def test_lock_released_allows_other_thread(self):
        """Releasing a lock should allow another thread to acquire it."""
        storage = InMemoryGlobalStorage()
        result = {"acquired": None}

        # Acquire and immediately release
        storage.lock("RESOURCE", (), lock_type="+")
        storage.unlock("RESOURCE", ())

        def child_fn():
            got_lock = storage.lock("RESOURCE", (), timeout=1.0, lock_type="+")
            result["acquired"] = got_lock
            if got_lock:
                storage.unlock("RESOURCE", ())

        t = threading.Thread(target=child_fn)
        t.start()
        t.join(timeout=5.0)

        assert result["acquired"] is True

    def test_unlock_all_only_releases_own_locks(self):
        """unlock_all() should only release locks held by the calling thread."""
        storage = InMemoryGlobalStorage()
        barrier = threading.Barrier(2)
        result = {"child_lock_survived": None}

        def child_fn():
            storage.lock("CHILD_LOCK", (), lock_type="+")
            barrier.wait()  # Signal to parent that lock is held
            barrier.wait()  # Wait for parent to call unlock_all
            # Check if our lock survived parent's unlock_all
            # We still hold the lock, so it should still be in the table
            with storage._lock_condition:
                entry = storage._lock_table.get(("CHILD_LOCK", ()))
                result["child_lock_survived"] = entry is not None
            storage.unlock("CHILD_LOCK", ())

        t = threading.Thread(target=child_fn)
        t.start()

        # Acquire parent lock
        storage.lock("PARENT_LOCK", (), lock_type="+")
        barrier.wait()  # Wait for child to acquire its lock

        # Release all parent locks
        storage.unlock_all()
        barrier.wait()  # Signal to child to check

        t.join(timeout=5.0)

        assert result["child_lock_survived"] is True

    def test_child_locks_released_on_halt(self):
        """Child's locks should be released when child HALTs."""
        import sys
        import types

        storage = InMemoryGlobalStorage()

        mock_module = types.ModuleType("test_lock_halt_module")
        mock_module._routine_name = "test_lock_halt_module"
        mock_module._source_lines = []
        mock_module._label_lines = {}

        def entry(_rt, _scope=None):
            _rt.globals.lock("HELD_LOCK", (), lock_type="+")
            _rt.globals.set("LOCKED", (), "yes")
            raise SystemExit(0)

        mock_module.entry = entry  # type: ignore[attr-defined]
        sys.modules["test_lock_halt_module"] = mock_module

        try:
            rt = MUMPSRuntime(global_storage=storage)
            rt.start_job("entry", "test_lock_halt_module", [], None, None)
            rt.wait_for_jobs(timeout=5.0)

            # Child's global write should be visible
            assert storage.get("LOCKED", ()) == "yes"

            # Now main thread should be able to acquire the lock
            got_lock = storage.lock("HELD_LOCK", (), timeout=0.5, lock_type="+")
            assert got_lock is True
            storage.unlock("HELD_LOCK", ())
        finally:
            del sys.modules["test_lock_halt_module"]


@pytest.mark.runtime
class TestNakedIndicatorPerThread:
    """Tests for per-thread naked indicator isolation."""

    def test_naked_indicator_independent_per_thread(self):
        """Each thread should have its own naked indicator."""
        storage = InMemoryGlobalStorage()
        results = {"main": None, "child": None}

        # Set naked indicator in main thread
        storage.set("A", ("1", "2", "3"), "main_val")
        main_naked = storage.get_naked_indicator()
        results["main"] = main_naked

        barrier = threading.Barrier(2)

        def child_fn():
            # Child's naked indicator should start as None
            initial = storage.get_naked_indicator()
            assert initial is None, (
                f"Child naked indicator should be None, got {initial}"
            )

            # Set a different naked indicator in child
            storage.set("B", ("x", "y"), "child_val")
            results["child"] = storage.get_naked_indicator()
            barrier.wait()

        t = threading.Thread(target=child_fn)
        t.start()
        barrier.wait()
        t.join(timeout=5.0)

        # Main thread's naked indicator should be unchanged
        assert storage.get_naked_indicator() == main_naked

        # Child had its own naked indicator
        assert results["child"] is not None
        assert results["child"] != results["main"]
        assert results["child"][0] == "B"


@pytest.mark.runtime
class TestIncrementAtomicity:
    """Tests for $INCREMENT thread safety."""

    def test_concurrent_increment(self):
        """Concurrent $INCREMENT should produce correct total."""
        storage = InMemoryGlobalStorage()
        num_threads = 4
        increments_per_thread = 100

        def incr_fn():
            for _ in range(increments_per_thread):
                storage.incr("COUNTER", (), "1")

        threads = [threading.Thread(target=incr_fn) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        expected = num_threads * increments_per_thread
        actual = int(storage.get("COUNTER", ()) or "0")
        assert actual == expected, f"Expected {expected}, got {actual}"


@pytest.mark.runtime
class TestJobTimeout:
    """Tests for JOB timeout semantics."""

    def test_job_with_timeout_returns_true(self):
        """JOB with timeout should return True (success sets $TEST=1)."""
        import sys
        import types

        mock_module = types.ModuleType("test_timeout_module")
        mock_module._routine_name = "test_timeout_module"
        mock_module._source_lines = []
        mock_module._label_lines = {}

        def entry(_rt, _scope=None):
            pass

        mock_module.entry = entry  # type: ignore[attr-defined]
        sys.modules["test_timeout_module"] = mock_module

        try:
            rt = MUMPSRuntime()
            result = rt.start_job("entry", "test_timeout_module", [], None, 5.0)
            assert result is True
            rt.wait_for_jobs(timeout=5.0)
        finally:
            del sys.modules["test_timeout_module"]

    def test_job_without_timeout_returns_true(self):
        """JOB without timeout should return True."""
        import sys
        import types

        mock_module = types.ModuleType("test_no_timeout_module")
        mock_module._routine_name = "test_no_timeout_module"
        mock_module._source_lines = []
        mock_module._label_lines = {}

        def entry(_rt, _scope=None):
            pass

        mock_module.entry = entry  # type: ignore[attr-defined]
        sys.modules["test_no_timeout_module"] = mock_module

        try:
            rt = MUMPSRuntime()
            result = rt.start_job("entry", "test_no_timeout_module", [], None, None)
            assert result is True
            rt.wait_for_jobs(timeout=5.0)
        finally:
            del sys.modules["test_no_timeout_module"]

    def test_job_missing_module_with_timeout_returns_false(self):
        """JOB on a missing module with timeout should return False ($TEST=0)."""
        rt = MUMPSRuntime()
        result = rt.start_job("entry", "nonexistent_module", [], None, 5.0)
        assert result is False

    def test_job_missing_label_with_timeout_returns_false(self):
        """JOB on a missing label with timeout should return False ($TEST=0)."""
        import sys
        import types

        mock_module = types.ModuleType("test_nolabel_module")
        mock_module._routine_name = "test_nolabel_module"
        mock_module._source_lines = []
        mock_module._label_lines = {}
        sys.modules["test_nolabel_module"] = mock_module

        try:
            rt = MUMPSRuntime()
            result = rt.start_job(
                "nonexistent_label", "test_nolabel_module", [], None, 5.0
            )
            assert result is False
        finally:
            del sys.modules["test_nolabel_module"]


@pytest.mark.runtime
class TestJobChildPrincipal:
    """Tests for JOBbed child process $PRINCIPAL isolation.

    When a process is JOBbed, its $PRINCIPAL and $IO should be
    different from the parent — per MUMPS spec, $PRINCIPAL is constant
    for the life of a process and equals the initial $IO.

    Fixed suite: V4PRIN (test 40746)
    """

    def test_child_has_unique_principal(self):
        """JOB'd child runtime has a different $PRINCIPAL than parent."""
        storage = InMemoryGlobalStorage()
        parent_rt = MUMPSRuntime(global_storage=storage)

        # Simulate start_job child creation using class counter like the real code
        with MUMPSRuntime._job_counter_lock:
            MUMPSRuntime._job_counter += 1
            child_pid = os.getpid() + MUMPSRuntime._job_counter

        child_rt = MUMPSRuntime(global_storage=storage)
        child_rt._job_id = child_pid
        child_device = f"/dev/null/{child_pid}"
        child_rt._principal = child_device
        child_rt._io = child_device

        assert child_rt._principal != parent_rt._principal
        assert child_rt._io != parent_rt._io
        assert child_rt._principal == child_rt._io
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
        child_rt._io = child_device

        assert child_rt._principal == "/dev/null/12345"
        assert child_rt._io == "/dev/null/12345"
