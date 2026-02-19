"""Tests for basic global operations across all backends.

Covers: get, set, kill, kill_all, data, kill_node
These tests use the `backend` fixture from conftest.py which
selects the appropriate backend via M2PY_GLOBAL_BACKEND env var.
"""

from __future__ import annotations


class TestGetSet:
    """Test get/set operations."""

    def test_set_and_get_simple(self, backend):
        backend.set("TEST", ("1",), "hello")
        assert backend.get("TEST", ("1",)) == "hello"

    def test_get_undefined_returns_none(self, backend):
        assert backend.get("TEST", ("1",)) is None

    def test_get_undefined_global_returns_none(self, backend):
        assert backend.get("NONEXISTENT", ()) is None

    def test_set_overwrites_value(self, backend):
        backend.set("TEST", ("1",), "first")
        backend.set("TEST", ("1",), "second")
        assert backend.get("TEST", ("1",)) == "second"

    def test_set_empty_string(self, backend):
        backend.set("TEST", ("1",), "")
        assert backend.get("TEST", ("1",)) == ""

    def test_set_numeric_string(self, backend):
        backend.set("TEST", ("1",), "42")
        assert backend.get("TEST", ("1",)) == "42"

    def test_set_at_root(self, backend):
        backend.set("TEST", (), "root_value")
        assert backend.get("TEST", ()) == "root_value"

    def test_set_deep_subscripts(self, backend):
        backend.set("TEST", ("a", "b", "c"), "deep")
        assert backend.get("TEST", ("a", "b", "c")) == "deep"

    def test_get_parent_without_value(self, backend):
        """Parent node without a value should return None."""
        backend.set("TEST", ("a", "b"), "child")
        assert backend.get("TEST", ("a",)) is None

    def test_multiple_subscripts_independent(self, backend):
        backend.set("TEST", ("1",), "one")
        backend.set("TEST", ("2",), "two")
        assert backend.get("TEST", ("1",)) == "one"
        assert backend.get("TEST", ("2",)) == "two"

    def test_set_special_characters(self, backend):
        """Test values with special characters."""
        backend.set("TEST", ("1",), "hello world")
        assert backend.get("TEST", ("1",)) == "hello world"

    def test_set_unicode_value(self, backend):
        backend.set("TEST", ("1",), "héllo wörld")
        assert backend.get("TEST", ("1",)) == "héllo wörld"


class TestData:
    """Test $DATA operation."""

    def test_data_undefined_returns_0(self, backend):
        assert backend.data("TEST", ("1",)) == 0

    def test_data_value_only_returns_1(self, backend):
        backend.set("TEST", ("1",), "value")
        assert backend.data("TEST", ("1",)) == 1

    def test_data_descendants_only_returns_10(self, backend):
        backend.set("TEST", ("1", "2"), "child")
        assert backend.data("TEST", ("1",)) == 10

    def test_data_value_and_descendants_returns_11(self, backend):
        backend.set("TEST", ("1",), "parent")
        backend.set("TEST", ("1", "2"), "child")
        assert backend.data("TEST", ("1",)) == 11

    def test_data_at_root(self, backend):
        backend.set("TEST", (), "root")
        d = backend.data("TEST", ())
        assert d in (1, 11)

    def test_data_root_with_children(self, backend):
        backend.set("TEST", ("1",), "child")
        d = backend.data("TEST", ())
        assert d == 10


class TestKill:
    """Test kill (delete subtree) operations."""

    def test_kill_single_node(self, backend):
        backend.set("TEST", ("1",), "value")
        backend.kill("TEST", ("1",))
        assert backend.get("TEST", ("1",)) is None
        assert backend.data("TEST", ("1",)) == 0

    def test_kill_subtree(self, backend):
        backend.set("TEST", ("1",), "parent")
        backend.set("TEST", ("1", "a"), "child_a")
        backend.set("TEST", ("1", "b"), "child_b")
        backend.kill("TEST", ("1",))
        assert backend.get("TEST", ("1",)) is None
        assert backend.get("TEST", ("1", "a")) is None
        assert backend.get("TEST", ("1", "b")) is None

    def test_kill_entire_global(self, backend):
        backend.set("TEST", ("1",), "one")
        backend.set("TEST", ("2",), "two")
        backend.kill("TEST", ())
        assert backend.get("TEST", ("1",)) is None
        assert backend.get("TEST", ("2",)) is None

    def test_kill_nonexistent_is_silent(self, backend):
        # Should not raise
        backend.kill("NONEXISTENT", ("1",))

    def test_kill_preserves_siblings(self, backend):
        backend.set("TEST", ("1",), "one")
        backend.set("TEST", ("2",), "two")
        backend.kill("TEST", ("1",))
        assert backend.get("TEST", ("1",)) is None
        assert backend.get("TEST", ("2",)) == "two"


class TestKillAll:
    """Test kill_all (reset) operation."""

    def test_kill_all_clears_everything(self, backend):
        backend.set("TEST1", ("1",), "val1")
        backend.set("TEST2", ("1",), "val2")
        backend.kill_all()
        assert backend.get("TEST1", ("1",)) is None
        assert backend.get("TEST2", ("1",)) is None

    def test_kill_all_resets_naked(self, backend):
        backend.set("TEST", ("1",), "val")
        backend.kill_all()
        assert backend.get_naked_indicator() is None


class TestKillNode:
    """Test kill_node (value-only kill, preserve descendants)."""

    def test_kill_node_preserves_descendants(self, backend):
        backend.set("TEST", ("1",), "parent")
        backend.set("TEST", ("1", "a"), "child")
        backend.kill_node("TEST", ("1",))
        assert backend.get("TEST", ("1",)) is None
        assert backend.get("TEST", ("1", "a")) == "child"

    def test_kill_node_leaf(self, backend):
        backend.set("TEST", ("1",), "value")
        backend.kill_node("TEST", ("1",))
        assert backend.get("TEST", ("1",)) is None
        assert backend.data("TEST", ("1",)) == 0

    def test_kill_node_nonexistent_is_silent(self, backend):
        # Should not raise
        backend.kill_node("NONEXISTENT", ("1",))

    def test_kill_node_data_becomes_10(self, backend):
        """After kill_node on a node with value+children, $DATA should be 10."""
        backend.set("TEST", ("1",), "parent")
        backend.set("TEST", ("1", "a"), "child")
        assert backend.data("TEST", ("1",)) == 11
        backend.kill_node("TEST", ("1",))
        assert backend.data("TEST", ("1",)) == 10
