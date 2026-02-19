"""Tests for MERGE operations (get_tree/merge_tree) across all backends.

Covers: get_tree returning MArray, merge_tree writing MArray to globals.
"""

from __future__ import annotations


from m2py.runtime import MArray


class TestGetTree:
    """Test get_tree returns correct MArray structure."""

    def test_get_tree_single_value(self, backend):
        backend.set("TEST", ("1",), "value")
        tree = backend.get_tree("TEST", ("1",))
        assert tree is not None
        assert tree._value == "value"

    def test_get_tree_with_children(self, backend):
        backend.set("TEST", ("1",), "parent")
        backend.set("TEST", ("1", "a"), "child_a")
        backend.set("TEST", ("1", "b"), "child_b")

        tree = backend.get_tree("TEST", ("1",))
        assert tree is not None
        assert tree._value == "parent"
        assert "a" in tree._children
        assert "b" in tree._children
        assert tree._children["a"]._value == "child_a"
        assert tree._children["b"]._value == "child_b"

    def test_get_tree_nonexistent_returns_none(self, backend):
        tree = backend.get_tree("TEST", ("1",))
        assert tree is None

    def test_get_tree_descendants_only(self, backend):
        """Node has descendants but no value."""
        backend.set("TEST", ("1", "a"), "child")
        tree = backend.get_tree("TEST", ("1",))
        assert tree is not None
        assert tree._value is None
        assert "a" in tree._children

    def test_get_tree_deep(self, backend):
        backend.set("TEST", ("1", "a", "x"), "deep")
        tree = backend.get_tree("TEST", ("1",))
        assert tree is not None
        assert "a" in tree._children
        assert "x" in tree._children["a"]._children
        assert tree._children["a"]._children["x"]._value == "deep"


class TestMergeTree:
    """Test merge_tree writes MArray to globals correctly."""

    def test_merge_simple(self, backend):
        source = MArray()
        source._value = "root"
        backend.merge_tree("TEST", ("1",), source)
        assert backend.get("TEST", ("1",)) == "root"

    def test_merge_with_children(self, backend):
        source = MArray()
        source._value = "parent"
        child_a = MArray()
        child_a._value = "child_a"
        child_b = MArray()
        child_b._value = "child_b"
        source._children["a"] = child_a
        source._children["b"] = child_b

        backend.merge_tree("TEST", ("1",), source)
        assert backend.get("TEST", ("1",)) == "parent"
        assert backend.get("TEST", ("1", "a")) == "child_a"
        assert backend.get("TEST", ("1", "b")) == "child_b"

    def test_merge_preserves_existing(self, backend):
        """MERGE should add to existing data, not replace."""
        backend.set("TEST", ("1", "existing"), "old")

        source = MArray()
        source._value = "new_root"
        backend.merge_tree("TEST", ("1",), source)

        assert backend.get("TEST", ("1",)) == "new_root"
        assert backend.get("TEST", ("1", "existing")) == "old"

    def test_roundtrip_get_merge(self, backend):
        """get_tree followed by merge_tree should reproduce the data."""
        backend.set("SRC", ("1",), "parent")
        backend.set("SRC", ("1", "a"), "child_a")
        backend.set("SRC", ("1", "b"), "child_b")

        tree = backend.get_tree("SRC", ("1",))
        assert tree is not None

        backend.merge_tree("DST", ("2",), tree)
        assert backend.get("DST", ("2",)) == "parent"
        assert backend.get("DST", ("2", "a")) == "child_a"
        assert backend.get("DST", ("2", "b")) == "child_b"
