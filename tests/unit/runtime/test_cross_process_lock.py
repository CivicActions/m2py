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
