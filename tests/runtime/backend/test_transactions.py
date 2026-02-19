"""Tests for transaction operations across all backends.

Covers: TSTART/TCOMMIT/TROLLBACK, $TLEVEL tracking, nested transactions,
rollback state restoration, atomicity, and isolation.
"""

from __future__ import annotations

import pytest


class TestTransactionBasic:
    """Test basic transaction operations."""

    def test_tlevel_initial_zero(self, backend):
        assert backend.get_tlevel() == 0

    def test_tstart_increments_level(self, backend):
        backend.transaction_start()
        assert backend.get_tlevel() == 1
        # Clean up
        backend.transaction_rollback()

    def test_tcommit_decrements_level(self, backend):
        backend.transaction_start()
        backend.transaction_commit()
        assert backend.get_tlevel() == 0

    def test_trollback_resets_level_to_zero(self, backend):
        backend.transaction_start()
        backend.transaction_start()
        assert backend.get_tlevel() == 2
        backend.transaction_rollback()
        assert backend.get_tlevel() == 0

    def test_tcommit_without_tstart_raises(self, backend):
        with pytest.raises(RuntimeError, match="M44"):
            backend.transaction_commit()

    def test_trollback_without_tstart_raises(self, backend):
        with pytest.raises(RuntimeError, match="M44"):
            backend.transaction_rollback()


class TestTransactionNested:
    """Test nested transaction level tracking."""

    def test_nested_increments(self, backend):
        backend.transaction_start()
        assert backend.get_tlevel() == 1
        backend.transaction_start()
        assert backend.get_tlevel() == 2
        backend.transaction_commit()
        assert backend.get_tlevel() == 1
        backend.transaction_commit()
        assert backend.get_tlevel() == 0

    def test_nested_rollback(self, backend):
        """TROLLBACK always sets $TLEVEL to 0."""
        backend.transaction_start()
        backend.transaction_start()
        backend.transaction_start()
        assert backend.get_tlevel() == 3
        backend.transaction_rollback()
        assert backend.get_tlevel() == 0


class TestTransactionData:
    """Test that data operations work within transactions."""

    def test_set_in_transaction(self, backend):
        backend.transaction_start()
        backend.set("TEST", ("1",), "in_txn")
        backend.transaction_commit()
        assert backend.get("TEST", ("1",)) == "in_txn"

    def test_get_in_transaction(self, backend):
        backend.set("TEST", ("1",), "before")
        backend.transaction_start()
        assert backend.get("TEST", ("1",)) == "before"
        backend.transaction_commit()


class TestTransactionRollback:
    """Test that rollback restores pre-transaction state (T080)."""

    def test_rollback_restores_set(self, backend):
        """SET inside rolled-back transaction should not persist."""
        backend.set("TEST", ("1",), "original")
        backend.transaction_start()
        backend.set("TEST", ("1",), "modified")
        backend.transaction_rollback()
        assert backend.get("TEST", ("1",)) == "original"

    def test_rollback_restores_kill(self, backend):
        """KILL inside rolled-back transaction should not persist."""
        backend.set("TEST", ("1",), "alive")
        backend.transaction_start()
        backend.kill("TEST", ("1",))
        backend.transaction_rollback()
        assert backend.get("TEST", ("1",)) == "alive"

    def test_rollback_restores_new_node(self, backend):
        """New node created in rolled-back transaction should not exist."""
        backend.transaction_start()
        backend.set("TEST", ("new",), "value")
        backend.transaction_rollback()
        assert backend.get("TEST", ("new",)) is None

    def test_rollback_restores_increment(self, backend, backend_name):
        """Increment inside rolled-back transaction should not persist.

        Note: IRIS $INCREMENT is non-transactional by design - it uses
        optimistic concurrency and does not participate in TROLLBACK.
        """
        if backend_name == "iris":
            pytest.skip("IRIS $INCREMENT is non-transactional by design")
        backend.set("TEST", ("counter",), "10")
        backend.transaction_start()
        backend.incr("TEST", ("counter",), "5")
        backend.transaction_rollback()
        assert backend.get("TEST", ("counter",)) == "10"

    def test_rollback_multiple_operations(self, backend):
        """Multiple operations in rolled-back transaction all revert."""
        backend.set("TEST", ("a",), "1")
        backend.set("TEST", ("b",), "2")
        backend.transaction_start()
        backend.set("TEST", ("a",), "changed")
        backend.kill("TEST", ("b",))
        backend.set("TEST", ("c",), "new")
        backend.transaction_rollback()
        assert backend.get("TEST", ("a",)) == "1"
        assert backend.get("TEST", ("b",)) == "2"
        assert backend.get("TEST", ("c",)) is None


class TestTransactionAtomicity:
    """Test all-or-nothing semantics (T082)."""

    def test_committed_changes_persist(self, backend):
        """All changes in committed transaction should persist."""
        backend.transaction_start()
        backend.set("TEST", ("x",), "1")
        backend.set("TEST", ("y",), "2")
        backend.set("TEST", ("z",), "3")
        backend.transaction_commit()
        assert backend.get("TEST", ("x",)) == "1"
        assert backend.get("TEST", ("y",)) == "2"
        assert backend.get("TEST", ("z",)) == "3"

    def test_multiple_globals_in_transaction(self, backend):
        """Transaction spans multiple globals."""
        backend.transaction_start()
        backend.set("A", ("1",), "val_a")
        backend.set("B", ("1",), "val_b")
        backend.transaction_commit()
        assert backend.get("A", ("1",)) == "val_a"
        assert backend.get("B", ("1",)) == "val_b"

    def test_rollback_multiple_globals(self, backend):
        """Rollback reverts changes across multiple globals."""
        backend.set("A", ("1",), "original_a")
        backend.set("B", ("1",), "original_b")
        backend.transaction_start()
        backend.set("A", ("1",), "modified_a")
        backend.set("B", ("1",), "modified_b")
        backend.transaction_rollback()
        assert backend.get("A", ("1",)) == "original_a"
        assert backend.get("B", ("1",)) == "original_b"


class TestTransactionIsolation:
    """Test read-committed isolation semantics (T083).

    Note: True cross-process isolation requires database backends.
    The inmemory backend provides basic visibility guarantees within a single process.
    """

    def test_uncommitted_reads_visible_within_transaction(self, backend):
        """Reads within transaction see own uncommitted writes."""
        backend.transaction_start()
        backend.set("TEST", ("1",), "in_txn")
        # Should see own write
        assert backend.get("TEST", ("1",)) == "in_txn"
        backend.transaction_rollback()

    def test_order_in_transaction(self, backend):
        """$ORDER works correctly within a transaction."""
        backend.set("TEST", ("a",), "1")
        backend.set("TEST", ("c",), "3")
        backend.transaction_start()
        backend.set("TEST", ("b",), "2")
        # Should see the new node in order
        result = backend.order("TEST", ("a",))
        assert result == "b"
        backend.transaction_commit()

    def test_data_in_transaction(self, backend):
        """$DATA works correctly within a transaction."""
        backend.transaction_start()
        backend.set("TEST", ("1",), "val")
        assert backend.data("TEST", ("1",)) in (1, 11)
        backend.transaction_commit()

    def test_incr_in_transaction(self, backend):
        """$INCREMENT works correctly within a transaction."""
        backend.set("TEST", ("counter",), "0")
        backend.transaction_start()
        result = backend.incr("TEST", ("counter",), "5")
        assert result == "5"
        backend.transaction_commit()
        assert backend.get("TEST", ("counter",)) == "5"
