"""Tests for cross-process LOCK operations via SQLite.

Spec 022 Phase 7 (T083-T088): Tests for SQLite-backed lock manager
including single-process backward compatibility, cross-process conflicts,
hierarchical blocking, dead-process detection, and ZSHOW "L".
"""

import os
import subprocess
import sys
import textwrap
import time

import pytest

from m2py.runtime.sqlite_storage import SQLiteGlobalStorage


@pytest.fixture
def db_path(tmp_path):
    """Shared SQLite database path."""
    return str(tmp_path / "lock_test.db")


@pytest.fixture
def storage(db_path):
    """Create a SQLiteGlobalStorage instance."""
    s = SQLiteGlobalStorage(db_path)
    yield s
    s.close()


# =========================================================================
# T083: Single-Process LOCK Backward Compatibility
# =========================================================================


class TestSingleProcessLockCompat:
    """Verify all existing LOCK patterns work with SQLite backend."""

    def test_incremental_lock_acquire(self, storage):
        """LOCK + acquires lock with count=1."""
        result = storage.lock("A", (), lock_type="+")
        assert result is True

    def test_incremental_lock_release(self, storage):
        """LOCK - decrements lock count."""
        storage.lock("A", (), lock_type="+")
        result = storage.lock("A", (), lock_type="-")
        assert result is True
        # Lock should be fully released
        assert storage.ssvn_lock("A") == ""

    def test_reentrant_lock(self, storage):
        """Same process can increment lock count."""
        storage.lock("A", (), lock_type="+")
        storage.lock("A", (), lock_type="+")
        assert storage.ssvn_lock("A") == "2"

        storage.lock("A", (), lock_type="-")
        assert storage.ssvn_lock("A") == "1"

        storage.lock("A", (), lock_type="-")
        assert storage.ssvn_lock("A") == ""

    def test_argumentless_lock_releases_all(self, storage):
        """unlock_all() releases all locks held by current process."""
        storage.lock("A", (), lock_type="+")
        storage.lock("B", ("1",), lock_type="+")
        storage.lock("C", (), lock_type="+")
        storage.unlock_all()
        assert storage.ssvn_lock("A") == ""
        assert storage.ssvn_lock("B") == ""
        assert storage.ssvn_lock("C") == ""

    def test_bare_lock_release_only_own(self, storage):
        """Release with wrong name does nothing."""
        storage.lock("A", (), lock_type="+")
        storage.lock("B", (), lock_type="-")  # B not held — no-op
        assert storage.ssvn_lock("A") == "1"

    def test_lock_with_subscripts(self, storage):
        """LOCK on subscripted names."""
        result = storage.lock("A", ("1", "2"), lock_type="+")
        assert result is True

    def test_lock_release_below_zero_noop(self, storage):
        """Releasing a lock not held is a no-op."""
        result = storage.lock("X", (), lock_type="-")
        assert result is True  # Still returns True

    def test_lock_timeout_zero_self(self, storage):
        """LOCK with timeout=0 succeeds immediately for own lock."""
        result = storage.lock("A", (), timeout=0.0, lock_type="+")
        assert result is True

    def test_unlock_method(self, storage):
        """unlock() decrements and removes."""
        storage.lock("A", (), lock_type="+")
        storage.lock("A", (), lock_type="+")  # count=2
        storage.unlock("A", ())  # count=1
        assert storage.ssvn_lock("A") == "1"
        storage.unlock("A", ())  # count=0
        assert storage.ssvn_lock("A") == ""


# =========================================================================
# T086: Hierarchical Lock Blocking
# =========================================================================


class TestHierarchicalBlockingSingleProcess:
    """Test hierarchical blocking rules within same process.

    Same process should be able to acquire parent AND child locks
    without conflict (no self-blocking).
    """

    def test_parent_and_child_same_process(self, storage):
        """Same process can hold ^A and ^A(1) simultaneously."""
        assert storage.lock("A", (), lock_type="+") is True
        assert storage.lock("A", ("1",), lock_type="+") is True

    def test_child_and_parent_same_process(self, storage):
        """Same process can hold ^A(1) and then ^A."""
        assert storage.lock("A", ("1",), lock_type="+") is True
        assert storage.lock("A", (), lock_type="+") is True

    def test_sibling_locks_same_process(self, storage):
        """Same process can hold ^A(1) and ^A(2)."""
        assert storage.lock("A", ("1",), lock_type="+") is True
        assert storage.lock("A", ("2",), lock_type="+") is True

    def test_deep_nested_same_process(self, storage):
        """Same process can hold ^A, ^A(1), ^A(1,2)."""
        assert storage.lock("A", (), lock_type="+") is True
        assert storage.lock("A", ("1",), lock_type="+") is True
        assert storage.lock("A", ("1", "2"), lock_type="+") is True


# =========================================================================
# T084: Cross-Process LOCK Conflict Tests
# =========================================================================


def _run_lock_child(
    db_path: str, lock_name: str, lock_subs: str, timeout: float, result_global: str
) -> subprocess.Popen:
    """Start a child process that attempts to acquire a lock.

    Writes "1" to result_global if lock acquired, "0" if timeout.
    """
    code = textwrap.dedent(f"""\
        import sys, json, time
        sys.path.insert(0, '')
        from m2py.runtime.sqlite_storage import SQLiteGlobalStorage
        storage = SQLiteGlobalStorage({db_path!r})
        subs = tuple(json.loads({lock_subs!r}))
        result = storage.lock({lock_name!r}, subs, timeout={timeout!r}, lock_type="+")
        storage.set({result_global!r}, (), "1" if result else "0")
        storage.close()
    """)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    return subprocess.Popen(
        [sys.executable, "-c", code],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


class TestCrossProcessLock:
    """Test cross-process lock conflicts via SQLite."""

    def test_conflict_exact_lock(self, storage, db_path):
        """Parent holds ^A, child can't acquire ^A with timeout=0."""
        storage.lock("A", (), lock_type="+")
        child = _run_lock_child(db_path, "A", "[]", 0.0, "child_result")
        child.wait(timeout=10)

        # Re-read from a fresh connection
        s2 = SQLiteGlobalStorage(db_path)
        assert s2.get("child_result", ()) == "0"  # Child timed out
        s2.close()

    def test_release_allows_acquire(self, storage, db_path):
        """Parent releases ^A, child can then acquire it."""
        storage.lock("A", (), lock_type="+")
        # Start child with 5s timeout — it will poll
        child = _run_lock_child(db_path, "A", "[]", 5.0, "child_result2")
        time.sleep(0.3)  # Let child start polling
        storage.unlock_all()  # Release the lock
        child.wait(timeout=10)

        s2 = SQLiteGlobalStorage(db_path)
        assert s2.get("child_result2", ()) == "1"  # Child acquired
        s2.close()

    def test_hierarchical_parent_blocks_child(self, storage, db_path):
        """Parent holds ^A, child can't acquire ^A(1)."""
        storage.lock("A", (), lock_type="+")
        child = _run_lock_child(db_path, "A", '["1"]', 0.0, "hier_result")
        child.wait(timeout=10)

        s2 = SQLiteGlobalStorage(db_path)
        assert s2.get("hier_result", ()) == "0"  # Blocked by parent
        s2.close()

    def test_hierarchical_child_blocks_parent(self, storage, db_path):
        """Parent holds ^A(1), child can't acquire ^A."""
        storage.lock("A", ("1",), lock_type="+")
        child = _run_lock_child(db_path, "A", "[]", 0.0, "hier_result2")
        child.wait(timeout=10)

        s2 = SQLiteGlobalStorage(db_path)
        assert s2.get("hier_result2", ()) == "0"  # Blocked by child lock
        s2.close()

    def test_sibling_no_conflict(self, storage, db_path):
        """Parent holds ^A(1), child can acquire ^A(2) — no conflict."""
        storage.lock("A", ("1",), lock_type="+")
        child = _run_lock_child(db_path, "A", '["2"]', 0.0, "sib_result")
        child.wait(timeout=10)

        s2 = SQLiteGlobalStorage(db_path)
        assert s2.get("sib_result", ()) == "1"  # No conflict
        s2.close()

    def test_different_name_no_conflict(self, storage, db_path):
        """Parent holds ^A, child can acquire ^B."""
        storage.lock("A", (), lock_type="+")
        child = _run_lock_child(db_path, "B", "[]", 0.0, "diff_result")
        child.wait(timeout=10)

        s2 = SQLiteGlobalStorage(db_path)
        assert s2.get("diff_result", ()) == "1"  # Different name, no conflict
        s2.close()


# =========================================================================
# T085: Dead-Process Lock Cleanup
# =========================================================================


class TestDeadProcessCleanup:
    """Test automatic cleanup of orphaned locks from dead processes."""

    def test_dead_process_lock_cleared(self, storage, db_path):
        """Lock from a dead process is auto-cleared during acquire."""
        # Insert a fake lock from a non-existent PID
        storage._conn.execute(
            "INSERT INTO locks (lock_name, subscripts, owner_pid, lock_count, acquired_at) "
            "VALUES (?, ?, ?, 1, ?)",
            ("DEAD", "[]", 99999999, time.time()),  # PID that doesn't exist
        )

        # Current process should be able to acquire it
        result = storage.lock("DEAD", (), timeout=0.0, lock_type="+")
        assert result is True

    def test_live_process_lock_not_cleared(self, storage, db_path):
        """Lock from a live process (our own PID) is NOT cleared."""
        # We hold a lock on A
        storage.lock("A", (), lock_type="+")

        # Start a child that tries to acquire A with timeout=0
        child = _run_lock_child(db_path, "A", "[]", 0.0, "live_result")
        child.wait(timeout=10)

        s2 = SQLiteGlobalStorage(db_path)
        assert s2.get("live_result", ()) == "0"  # Our process is alive, blocked
        s2.close()


# =========================================================================
# T087: ZSHOW "L" Output Format
# =========================================================================


class TestZshowLocks:
    """Test ZSHOW 'L' lock display via MUMPSRuntime."""

    def test_zshow_l_no_locks(self, db_path):
        """ZSHOW "L" with no locks shows MLG:0."""
        from m2py.runtime import MUMPSRuntime

        storage = SQLiteGlobalStorage(db_path)
        rt = MUMPSRuntime(global_storage=storage)
        output = []
        rt.write = lambda s: output.append(s)
        rt.zshow("L", {})
        text = "".join(output)
        assert "MLG:0" in text
        storage.close()

    def test_zshow_l_with_locks(self, db_path):
        """ZSHOW "L" shows held locks with level."""
        from m2py.runtime import MUMPSRuntime

        storage = SQLiteGlobalStorage(db_path)
        rt = MUMPSRuntime(global_storage=storage)
        storage.lock("A", (), lock_type="+")
        storage.lock("B", ("1",), lock_type="+")

        output = []
        rt.write = lambda s: output.append(s)
        rt.zshow("L", {})
        text = "".join(output)
        assert "MLG:2" in text
        assert "LOCK ^A LEVEL=1" in text or "LOCK ^B" in text
        storage.close()


# =========================================================================
# T088: Cross-Process LOCK Integration (JOB + LOCK)
# =========================================================================


class TestJobLockIntegration:
    """Test LOCK behavior with JOB'd child processes."""

    def test_parent_lock_blocks_jobbed_child(self, db_path, tmp_path):
        """Parent holds lock, JOB'd child can't acquire it."""
        from m2py.runtime import MUMPSRuntime

        storage = SQLiteGlobalStorage(db_path)
        rt = MUMPSRuntime(global_storage=storage)

        # Parent acquires lock
        storage.lock("LCK", (), lock_type="+")

        # Create child routine that tries to acquire same lock
        routine_dir = tmp_path / "routines"
        routine_dir.mkdir()
        (routine_dir / "LOCKCHLD.py").write_text(
            textwrap.dedent("""\
            def LOCKCHLD(_rt, _scope=None):
                result = _rt.globals.lock("LCK", (), timeout=0.0, lock_type="+")
                _rt.globals.set("lockresult", (), "1" if result else "0")
            """)
        )
        sys.path.insert(0, str(routine_dir))
        try:
            rt.start_job("LOCKCHLD", "LOCKCHLD", [], None, None)

            # Wait for child to write result
            deadline = time.monotonic() + 10.0
            while time.monotonic() < deadline:
                val = storage.get("lockresult", ())
                if val is not None:
                    break
                time.sleep(0.1)

            assert storage.get("lockresult", ()) == "0"  # Child was blocked
        finally:
            rt.cleanup()
            sys.path.remove(str(routine_dir))
            storage.close()


# =========================================================================
# Indefinite-Wait Lock Tests (V3LOCK root cause)
# =========================================================================


def _run_indefinite_lock_child(
    db_path: str, lock_name: str, lock_subs: str, result_global: str
) -> subprocess.Popen:
    """Start a child that acquires a lock with NO timeout (indefinite wait).

    This is the pattern used by MUMPS ``LOCK +^VA`` — no timeout means
    "wait forever until the lock becomes available".

    Writes "1" to result_global after lock acquisition, plus timestamp.
    """
    code = textwrap.dedent(f"""\
        import sys, json, time
        sys.path.insert(0, '')
        from m2py.runtime.sqlite_storage import SQLiteGlobalStorage
        storage = SQLiteGlobalStorage({db_path!r})
        subs = tuple(json.loads({lock_subs!r}))
        # timeout=None means indefinite wait (MUMPS LOCK +^VA with no timeout)
        result = storage.lock({lock_name!r}, subs, timeout=None, lock_type="+")
        storage.set({result_global!r}, (), "1" if result else "0")
        storage.set({result_global!r}, ("t",), str(time.monotonic()))
        storage.close()
    """)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    return subprocess.Popen(
        [sys.executable, "-c", code],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


class TestIndefiniteWaitLock:
    """Test that lock(timeout=None) blocks until the lock is available.

    This is the root cause of V3LOCK YDB failures: the YDB backend was
    passing timeout_nsec=0 (non-blocking) for indefinite waits, causing
    child processes to fail immediately instead of waiting for the parent
    to release.
    """

    def test_indefinite_wait_blocks_then_succeeds(self, storage, db_path):
        """Child with timeout=None blocks until parent releases."""
        # Parent acquires lock
        storage.lock("INDEF", (), lock_type="+")

        # Child tries to lock with timeout=None (indefinite wait)
        child = _run_indefinite_lock_child(db_path, "INDEF", "[]", "indef_result")

        # Give child time to start and begin blocking
        time.sleep(0.5)

        # Verify child has NOT acquired the lock yet
        s_check = SQLiteGlobalStorage(db_path)
        assert s_check.get("indef_result", ()) is None, (
            "Child should be blocking, not yet returned"
        )
        s_check.close()

        # Parent releases the lock
        storage.unlock_all()

        # Child should now acquire and finish
        child.wait(timeout=15)

        s2 = SQLiteGlobalStorage(db_path)
        assert s2.get("indef_result", ()) == "1", (
            "Child should have acquired lock after parent released"
        )
        s2.close()

    def test_indefinite_wait_conflict_timeout_zero_vs_none(self, storage, db_path):
        """timeout=0 fails immediately; timeout=None blocks (key distinction)."""
        storage.lock("COMP", (), lock_type="+")

        # timeout=0: should fail immediately
        child_zero = _run_lock_child(db_path, "COMP", "[]", 0.0, "zero_result")
        child_zero.wait(timeout=10)

        s2 = SQLiteGlobalStorage(db_path)
        assert s2.get("zero_result", ()) == "0", (
            "timeout=0 should fail immediately when lock held"
        )
        s2.close()

        # timeout=None: should block until released
        child_none = _run_indefinite_lock_child(db_path, "COMP", "[]", "none_result")
        time.sleep(0.5)

        s3 = SQLiteGlobalStorage(db_path)
        assert s3.get("none_result", ()) is None, "Should be blocking"
        s3.close()

        storage.unlock_all()
        child_none.wait(timeout=15)

        s4 = SQLiteGlobalStorage(db_path)
        assert s4.get("none_result", ()) == "1", "Should succeed after release"
        s4.close()

    def test_indefinite_wait_with_subscripts(self, storage, db_path):
        """Indefinite wait works for subscripted lock names."""
        storage.lock("SUB", ("1", "2"), lock_type="+")

        child = _run_indefinite_lock_child(db_path, "SUB", '["1", "2"]', "sub_result")

        time.sleep(0.5)
        s_check = SQLiteGlobalStorage(db_path)
        assert s_check.get("sub_result", ()) is None
        s_check.close()

        storage.unlock_all()
        child.wait(timeout=15)

        s2 = SQLiteGlobalStorage(db_path)
        assert s2.get("sub_result", ()) == "1"
        s2.close()

    def test_indefinite_wait_hierarchical_blocking(self, storage, db_path):
        """Parent holds ^A, child LOCK +^A(1):None blocks on hierarchy."""
        storage.lock("HIER", (), lock_type="+")

        child = _run_indefinite_lock_child(db_path, "HIER", '["1"]', "hier_indef")
        time.sleep(0.5)

        s_check = SQLiteGlobalStorage(db_path)
        assert s_check.get("hier_indef", ()) is None, (
            "Child blocked by parent's hierarchical lock"
        )
        s_check.close()

        storage.unlock_all()
        child.wait(timeout=15)

        s2 = SQLiteGlobalStorage(db_path)
        assert s2.get("hier_indef", ()) == "1"
        s2.close()

    def test_indefinite_wait_no_conflict_proceeds(self, storage, db_path):
        """Indefinite wait with no conflict acquires immediately."""
        # Don't lock anything — child should get lock right away
        child = _run_indefinite_lock_child(db_path, "FREE", "[]", "free_result")
        child.wait(timeout=10)

        s2 = SQLiteGlobalStorage(db_path)
        assert s2.get("free_result", ()) == "1"
        s2.close()
