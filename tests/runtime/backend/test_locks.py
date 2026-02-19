"""Tests for LOCK operations across all backends.

Covers: lock acquire/release, unlock, unlock_all, get_locks, timeout,
nested locks, multi-threaded safety.
"""

from __future__ import annotations

import threading


class TestLockBasic:
    """Test basic lock operations."""

    def test_lock_acquire(self, backend):
        result = backend.lock("TEST", ("1",))
        assert result is True

    def test_lock_and_unlock(self, backend):
        backend.lock("TEST", ("1",))
        backend.unlock("TEST", ("1",))
        # Should be able to re-acquire
        result = backend.lock("TEST", ("1",))
        assert result is True

    def test_unlock_all(self, backend):
        backend.lock("TEST", ("1",))
        backend.lock("OTHER", ("2",))
        backend.unlock_all()
        locks = backend.get_locks()
        assert len(locks) == 0

    def test_get_locks_empty(self, backend):
        locks = backend.get_locks()
        assert len(locks) == 0

    def test_get_locks_after_acquire(self, backend):
        backend.lock("TEST", ("1",))
        locks = backend.get_locks()
        assert len(locks) == 1

    def test_lock_type_release(self, backend):
        """Lock type '-' should release."""
        backend.lock("TEST", ("1",))
        result = backend.lock("TEST", ("1",), lock_type="-")
        assert result is True
        locks = backend.get_locks()
        assert len(locks) == 0


class TestLockNested:
    """Test nested lock counting."""

    def test_nested_lock_increment(self, backend):
        backend.lock("TEST", ("1",))
        backend.lock("TEST", ("1",))
        locks = backend.get_locks()
        # Should have 1 entry with count 2
        assert len(locks) == 1
        assert locks[0][2] == 2

    def test_nested_unlock_decrement(self, backend):
        backend.lock("TEST", ("1",))
        backend.lock("TEST", ("1",))
        backend.unlock("TEST", ("1",))
        locks = backend.get_locks()
        # Should still have 1 entry with count 1
        assert len(locks) == 1
        assert locks[0][2] == 1

    def test_full_unlock_removes_entry(self, backend):
        backend.lock("TEST", ("1",))
        backend.lock("TEST", ("1",))
        backend.unlock("TEST", ("1",))
        backend.unlock("TEST", ("1",))
        locks = backend.get_locks()
        assert len(locks) == 0


class TestLockTimeout:
    """Test lock timeout behavior."""

    def test_lock_with_zero_timeout(self, backend):
        """Lock with 0 timeout should succeed immediately if available."""
        result = backend.lock("TEST", ("1",), timeout=0)
        assert result is True


class TestLockMultipleResources:
    """Test locking on different resources simultaneously."""

    def test_lock_different_globals(self, backend):
        """Can lock on completely different globals."""
        r1 = backend.lock("A", ("1",))
        r2 = backend.lock("B", ("1",))
        assert r1 is True
        assert r2 is True
        locks = backend.get_locks()
        assert len(locks) == 2

    def test_lock_different_subscripts(self, backend):
        """Can lock on different subscripts of the same global."""
        r1 = backend.lock("TEST", ("1",))
        r2 = backend.lock("TEST", ("2",))
        assert r1 is True
        assert r2 is True
        locks = backend.get_locks()
        assert len(locks) == 2

    def test_unlock_specific_only(self, backend):
        """Unlocking one resource doesn't affect others."""
        backend.lock("A", ("1",))
        backend.lock("B", ("1",))
        backend.unlock("A", ("1",))
        locks = backend.get_locks()
        assert len(locks) == 1
        assert locks[0][0] == "B"


class TestThreadSafety:
    """Test thread safety of backend operations."""

    def test_concurrent_set_get(self, backend):
        """Multiple threads can set/get without corruption."""
        errors = []
        barrier = threading.Barrier(4)

        def worker(thread_id):
            try:
                barrier.wait(timeout=5)
                key = str(thread_id)
                for i in range(50):
                    backend.set("THREAD", (key, str(i)), f"t{thread_id}_{i}")
                for i in range(50):
                    val = backend.get("THREAD", (key, str(i)))
                    if val != f"t{thread_id}_{i}":
                        errors.append(
                            f"Thread {thread_id}: expected t{thread_id}_{i}, got {val}"
                        )
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert errors == [], f"Thread errors: {errors}"

    def test_concurrent_increment(self, backend):
        """Concurrent increments produce correct total."""
        num_threads = 4
        increments_per_thread = 25
        errors = []
        barrier = threading.Barrier(num_threads)

        def worker():
            try:
                barrier.wait(timeout=5)
                for _ in range(increments_per_thread):
                    backend.incr("COUNTER", ("total",), "1")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert errors == [], f"Thread errors: {errors}"
        val = backend.get("COUNTER", ("total",))
        expected = str(num_threads * increments_per_thread)
        assert val == expected
