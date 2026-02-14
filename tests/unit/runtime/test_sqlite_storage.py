"""Unit tests for SQLiteGlobalStorage backend.

Spec 022 Phase 4 T056-T057: Tests covering SET/GET/KILL/MERGE/$DATA/$ORDER/$QUERY/$INCREMENT
and transaction support (TSTART/TCOMMIT/TROLLBACK).

These tests mirror the InMemoryGlobalStorage tests to ensure identical behavior.
"""

import os
import pytest
from m2py.runtime.sqlite_storage import SQLiteGlobalStorage
from m2py.runtime import MArray


@pytest.fixture
def storage(tmp_path):
    """Create a fresh SQLiteGlobalStorage for each test."""
    db_path = str(tmp_path / "test.db")
    s = SQLiteGlobalStorage(db_path)
    yield s
    s.close()


# =============================================================================
# SET / GET (T047)
# =============================================================================


class TestSetGet:
    def test_set_and_get_root(self, storage):
        storage.set("X", (), "hello")
        assert storage.get("X", ()) == "hello"

    def test_set_and_get_subscripted(self, storage):
        storage.set("X", ("1",), "val1")
        storage.set("X", ("2",), "val2")
        assert storage.get("X", ("1",)) == "val1"
        assert storage.get("X", ("2",)) == "val2"

    def test_set_and_get_nested(self, storage):
        storage.set("X", ("1", "2", "3"), "deep")
        assert storage.get("X", ("1", "2", "3")) == "deep"

    def test_get_undefined(self, storage):
        assert storage.get("X", ()) is None
        assert storage.get("X", ("1",)) is None

    def test_set_overwrites(self, storage):
        storage.set("X", ("1",), "old")
        storage.set("X", ("1",), "new")
        assert storage.get("X", ("1",)) == "new"

    def test_empty_string_value(self, storage):
        storage.set("X", (), "")
        assert storage.get("X", ()) == ""

    def test_numeric_subscript_canonicalization(self, storage):
        storage.set("X", (1,), "one")  # type: ignore
        assert storage.get("X", ("1",)) == "one"

    def test_multiple_globals(self, storage):
        storage.set("A", (), "alpha")
        storage.set("B", (), "beta")
        assert storage.get("A", ()) == "alpha"
        assert storage.get("B", ()) == "beta"


# =============================================================================
# KILL (T048)
# =============================================================================


class TestKill:
    def test_kill_entire_global(self, storage):
        storage.set("X", (), "root")
        storage.set("X", ("1",), "child")
        storage.kill("X", ())
        assert storage.get("X", ()) is None
        assert storage.get("X", ("1",)) is None

    def test_kill_subtree(self, storage):
        storage.set("X", ("1",), "a")
        storage.set("X", ("1", "2"), "b")
        storage.set("X", ("1", "3"), "c")
        storage.set("X", ("2",), "d")
        storage.kill("X", ("1",))
        assert storage.get("X", ("1",)) is None
        assert storage.get("X", ("1", "2")) is None
        assert storage.get("X", ("1", "3")) is None
        assert storage.get("X", ("2",)) == "d"

    def test_kill_nonexistent(self, storage):
        # Should not raise
        storage.kill("X", ("99",))

    def test_kill_cleans_empty_ancestors(self, storage):
        storage.set("V1", ("2", "1"), "val")
        storage.kill("V1", ("2", "1"))
        assert storage.data("V1", ("2",)) == 0
        assert storage.data("V1", ()) == 0

    def test_kill_preserves_valued_ancestor(self, storage):
        storage.set("V1", ("2",), "parent")
        storage.set("V1", ("2", "1"), "child")
        storage.kill("V1", ("2", "1"))
        assert storage.data("V1", ("2",)) == 1
        assert storage.get("V1", ("2",)) == "parent"


class TestKillAll:
    def test_kill_all(self, storage):
        storage.set("A", (), "1")
        storage.set("B", ("1",), "2")
        storage.kill_all()
        assert storage.get("A", ()) is None
        assert storage.get("B", ("1",)) is None


# =============================================================================
# $DATA (T049)
# =============================================================================


class TestData:
    def test_undefined(self, storage):
        assert storage.data("X", ()) == 0

    def test_defined_no_children(self, storage):
        storage.set("X", (), "val")
        assert storage.data("X", ()) == 1

    def test_undefined_has_children(self, storage):
        storage.set("X", ("1",), "child")
        assert storage.data("X", ()) == 10

    def test_defined_and_has_children(self, storage):
        storage.set("X", (), "root")
        storage.set("X", ("1",), "child")
        assert storage.data("X", ()) == 11

    def test_data_subscripted(self, storage):
        storage.set("X", ("1", "2"), "deep")
        assert storage.data("X", ("1",)) == 10
        assert storage.data("X", ("1", "2")) == 1
        assert storage.data("X", ("1", "3")) == 0


# =============================================================================
# $ORDER (T050)
# =============================================================================


class TestOrder:
    def test_order_forward(self, storage):
        storage.set("X", ("A",), "1")
        storage.set("X", ("B",), "2")
        storage.set("X", ("C",), "3")
        assert storage.order("X", ("",)) == "A"
        assert storage.order("X", ("A",)) == "B"
        assert storage.order("X", ("B",)) == "C"
        assert storage.order("X", ("C",)) == ""

    def test_order_reverse(self, storage):
        storage.set("X", ("A",), "1")
        storage.set("X", ("B",), "2")
        storage.set("X", ("C",), "3")
        assert storage.order("X", ("",), direction=-1) == "C"
        assert storage.order("X", ("C",), direction=-1) == "B"
        assert storage.order("X", ("B",), direction=-1) == "A"
        assert storage.order("X", ("A",), direction=-1) == ""

    def test_order_numeric_before_string(self, storage):
        storage.set("X", ("1",), "num1")
        storage.set("X", ("2",), "num2")
        storage.set("X", ("A",), "strA")
        assert storage.order("X", ("",)) == "1"
        assert storage.order("X", ("1",)) == "2"
        assert storage.order("X", ("2",)) == "A"

    def test_order_negative_numbers(self, storage):
        storage.set("X", ("-2",), "neg2")
        storage.set("X", ("-1",), "neg1")
        storage.set("X", ("0",), "zero")
        storage.set("X", ("1",), "pos1")
        assert storage.order("X", ("",)) == "-2"
        assert storage.order("X", ("-2",)) == "-1"
        assert storage.order("X", ("-1",)) == "0"
        assert storage.order("X", ("0",)) == "1"

    def test_order_empty_global(self, storage):
        assert storage.order("X", ("",)) == ""

    def test_order_no_subscripts(self, storage):
        assert storage.order("X", ()) == ""

    def test_order_nested_subscripts(self, storage):
        storage.set("X", ("1", "A"), "val")
        storage.set("X", ("1", "B"), "val")
        storage.set("X", ("1", "C"), "val")
        assert storage.order("X", ("1", "")) == "A"
        assert storage.order("X", ("1", "A")) == "B"
        assert storage.order("X", ("1", "B")) == "C"
        assert storage.order("X", ("1", "C")) == ""

    def test_order_includes_valueless_nodes(self, storage):
        """$ORDER finds subscripts at a level even if they only have descendants."""
        storage.set("X", ("1", "A"), "val")
        # Node ("1",) has no value but has children
        assert storage.order("X", ("",)) == "1"


# =============================================================================
# $QUERY (T051)
# =============================================================================


class TestQuery:
    def test_query_basic(self, storage):
        storage.set("G", ("1",), "a")
        storage.set("G", ("2",), "b")
        assert storage.query("G", ("",)) == "^G(1)"
        assert storage.query("G", ("1",)) == "^G(2)"
        assert storage.query("G", ("2",)) == ""

    def test_query_nested(self, storage):
        storage.set("G", ("1", "2"), "a")
        storage.set("G", ("1", "3"), "b")
        storage.set("G", ("2",), "c")
        assert storage.query("G", ("",)) == "^G(1,2)"
        assert storage.query("G", ("1", "2")) == "^G(1,3)"
        assert storage.query("G", ("1", "3")) == "^G(2)"
        assert storage.query("G", ("2",)) == ""

    def test_query_empty_global(self, storage):
        assert storage.query("G", ("",)) == ""

    def test_query_skips_valueless_nodes(self, storage):
        """$QUERY only returns nodes with actual values."""
        storage.set("G", ("1", "2"), "val")
        # Node ("1",) exists as ancestor but has no value
        result = storage.query("G", ("",))
        assert result == "^G(1,2)"

    def test_query_string_subscripts_quoted(self, storage):
        storage.set("G", ("hello",), "val")
        result = storage.query("G", ("",))
        assert result == '^G("hello")'


# =============================================================================
# MERGE (T052)
# =============================================================================


class TestMerge:
    def test_get_tree(self, storage):
        storage.set("X", ("1",), "a")
        storage.set("X", ("1", "2"), "b")
        tree = storage.get_tree("X", ("1",))
        assert tree is not None
        assert tree._value == "a"
        assert "2" in tree._children
        assert tree._children["2"]._value == "b"

    def test_get_tree_undefined(self, storage):
        assert storage.get_tree("X", ("99",)) is None

    def test_merge_tree(self, storage):
        source = MArray()
        source._value = "root"
        child = MArray()
        child._value = "child1"
        source._children["1"] = child
        storage.merge_tree("X", (), source)
        assert storage.get("X", ()) == "root"
        assert storage.get("X", ("1",)) == "child1"

    def test_merge_preserves_existing(self, storage):
        storage.set("X", ("A",), "existing")
        source = MArray()
        child = MArray()
        child._value = "new"
        source._children["B"] = child
        storage.merge_tree("X", (), source)
        assert storage.get("X", ("A",)) == "existing"
        assert storage.get("X", ("B",)) == "new"


# =============================================================================
# $INCREMENT (T053)
# =============================================================================


class TestIncrement:
    def test_increment_undefined(self, storage):
        result = storage.incr("X", ("1",))
        assert result == "1"
        assert storage.get("X", ("1",)) == "1"

    def test_increment_existing(self, storage):
        storage.set("X", ("1",), "5")
        result = storage.incr("X", ("1",))
        assert result == "6"

    def test_increment_by_amount(self, storage):
        storage.set("X", ("1",), "10")
        result = storage.incr("X", ("1",), "3")
        assert result == "13"

    def test_increment_negative(self, storage):
        storage.set("X", ("1",), "10")
        result = storage.incr("X", ("1",), "-3")
        assert result == "7"

    def test_increment_decimal(self, storage):
        storage.set("X", ("1",), "1.5")
        result = storage.incr("X", ("1",), ".5")
        assert result == "2"


# =============================================================================
# KILL_NODE (ZKILL)
# =============================================================================


class TestKillNode:
    def test_kill_node_preserves_children(self, storage):
        storage.set("X", ("1",), "parent")
        storage.set("X", ("1", "2"), "child")
        storage.kill_node("X", ("1",))
        assert storage.get("X", ("1",)) is None
        assert storage.get("X", ("1", "2")) == "child"
        assert storage.data("X", ("1",)) == 10

    def test_kill_node_no_children(self, storage):
        storage.set("X", ("1",), "val")
        storage.kill_node("X", ("1",))
        assert storage.get("X", ("1",)) is None
        assert storage.data("X", ("1",)) == 0


# =============================================================================
# Naked Reference Operations
# =============================================================================


class TestNakedRef:
    def test_get_updates_naked(self, storage):
        storage.set("G", ("1", "2"), "val")
        storage.get("G", ("1", "2"))
        ni = storage.get_naked_indicator()
        assert ni == ("G", ("1",))

    def test_resolve_naked(self, storage):
        storage.set("G", ("1", "2"), "val")
        storage.get("G", ("1", "2"))
        name, subs = storage.resolve_naked(("3",))
        assert name == "G"
        assert subs == ("1", "3")

    def test_resolve_naked_error(self, storage):
        with pytest.raises(RuntimeError, match="NAKEDERR"):
            storage.resolve_naked(("1",))

    def test_set_naked_indicator(self, storage):
        storage.set_naked_indicator("X", ("1", "2"))
        assert storage.get_naked_indicator() == ("X", ("1", "2"))

    def test_root_access_clears_naked(self, storage):
        storage.set("G", ("1",), "val")
        storage.get("G", ())
        assert storage.get_naked_indicator() is None


# =============================================================================
# Transaction Support (T054/T057)
# =============================================================================


class TestTransactions:
    def test_tlevel_initially_zero(self, storage):
        assert storage.get_tlevel() == 0

    def test_tstart_increments_tlevel(self, storage):
        storage.transaction_start()
        assert storage.get_tlevel() == 1

    def test_tcommit_decrements_tlevel(self, storage):
        storage.transaction_start()
        storage.transaction_commit()
        assert storage.get_tlevel() == 0

    def test_tcommit_without_tstart_raises(self, storage):
        with pytest.raises(RuntimeError, match="M44"):
            storage.transaction_commit()

    def test_trollback_without_tstart_raises(self, storage):
        with pytest.raises(RuntimeError, match="M44"):
            storage.transaction_rollback()

    def test_transaction_commit_preserves_data(self, storage):
        storage.transaction_start()
        storage.set("X", (), "committed")
        storage.transaction_commit()
        assert storage.get("X", ()) == "committed"

    def test_transaction_rollback_reverts_set(self, storage):
        storage.set("X", (), "before")
        storage.transaction_start()
        storage.set("X", (), "during")
        assert storage.get("X", ()) == "during"
        storage.transaction_rollback()
        assert storage.get("X", ()) == "before"

    def test_transaction_rollback_reverts_new_global(self, storage):
        storage.transaction_start()
        storage.set("NEW", (), "created")
        storage.transaction_rollback()
        assert storage.get("NEW", ()) is None

    def test_nested_transactions(self, storage):
        storage.set("X", (), "level0")
        storage.transaction_start()  # level 1
        storage.set("X", (), "level1")
        storage.transaction_start()  # level 2
        storage.set("X", (), "level2")
        assert storage.get_tlevel() == 2
        # TROLLBACK rolls back ALL levels per MUMPS spec
        storage.transaction_rollback()
        assert storage.get_tlevel() == 0
        assert storage.get("X", ()) == "level0"

    def test_nested_commit_then_rollback(self, storage):
        storage.set("X", (), "original")
        storage.transaction_start()  # level 1
        storage.set("X", (), "modified")
        storage.transaction_start()  # level 2
        storage.set("Y", (), "added")
        storage.transaction_commit()  # commit level 2 into level 1
        assert storage.get_tlevel() == 1
        # Now rollback level 1 — should revert both X and Y
        storage.transaction_rollback()
        assert storage.get("X", ()) == "original"
        assert storage.get("Y", ()) is None


# =============================================================================
# Lock Operations (basic single-process)
# =============================================================================


class TestLocks:
    def test_lock_acquire(self, storage):
        result = storage.lock("A", ())
        assert result is True

    def test_lock_release(self, storage):
        storage.lock("A", ())
        result = storage.lock("A", (), lock_type="-")
        assert result is True

    def test_lock_reentrant(self, storage):
        storage.lock("A", ())
        storage.lock("A", ())
        # Should need two releases
        storage.lock("A", (), lock_type="-")
        # Still locked (count was 2, now 1)
        storage.lock("A", (), lock_type="-")
        # Now fully released

    def test_unlock_all(self, storage):
        storage.lock("A", ())
        storage.lock("B", ("1",))
        storage.unlock_all()
        # Locks should be released (no assertion needed — just no hang)

    def test_lock_timeout(self, storage):
        # With only one process, lock should always succeed
        result = storage.lock("A", (), timeout=0.1)
        assert result is True


# =============================================================================
# SSVN Queries
# =============================================================================


class TestSSVN:
    def test_ssvn_global_exists(self, storage):
        storage.set("TEST", (), "val")
        assert storage.ssvn_global("TEST") == "1"

    def test_ssvn_global_not_exists(self, storage):
        assert storage.ssvn_global("NOPE") == ""

    def test_ssvn_job_current(self, storage):
        assert storage.ssvn_job(str(os.getpid())) == "1"

    def test_ssvn_job_nonexistent(self, storage):
        assert storage.ssvn_job("999999999") == ""

    def test_ssvn_lock_unlocked(self, storage):
        assert storage.ssvn_lock("A") == ""

    def test_ssvn_lock_locked(self, storage):
        storage.lock("A", ())
        assert storage.ssvn_lock("A") == "1"


# =============================================================================
# Namespace Operations
# =============================================================================


class TestNamespace:
    def test_set_get_with_namespace(self, storage):
        storage.set_ns("X", ("1",), "val", namespace="NS1")
        assert storage.get_ns("X", ("1",), namespace="NS1") == "val"
        assert storage.get_ns("X", ("1",), namespace="NS2") is None

    def test_data_with_namespace(self, storage):
        storage.set_ns("X", ("1",), "val", namespace="NS1")
        assert storage.data_ns("X", ("1",), namespace="NS1") == 1
        assert storage.data_ns("X", ("1",), namespace="NS2") == 0


# =============================================================================
# Protocol Compliance
# =============================================================================


class TestProtocolCompliance:
    def test_is_global_storage_backend(self, storage):
        from m2py.runtime.globals import GlobalStorageBackend

        assert isinstance(storage, GlobalStorageBackend)


# =============================================================================
# Cross-Process Persistence
# =============================================================================


class TestPersistence:
    def test_data_persists_across_connections(self, tmp_path):
        """Data written by one connection is readable by another."""
        db_path = str(tmp_path / "shared.db")

        s1 = SQLiteGlobalStorage(db_path)
        s1.set("SHARED", ("1",), "hello")
        s1.close()

        s2 = SQLiteGlobalStorage(db_path)
        assert s2.get("SHARED", ("1",)) == "hello"
        s2.close()
