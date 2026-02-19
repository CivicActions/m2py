"""Tests for $ORDER and $QUERY traversal operations across all backends.

Covers: order (forward/reverse), query, naked indicator updates during traversal.
"""

from __future__ import annotations


class TestOrder:
    """Test $ORDER (subscript_next/previous) operations."""

    def test_order_forward_first(self, backend):
        """$ORDER with empty start returns first subscript."""
        backend.set("TEST", ("a",), "val_a")
        backend.set("TEST", ("b",), "val_b")
        backend.set("TEST", ("c",), "val_c")
        result = backend.order("TEST", ("",))
        assert result == "a"

    def test_order_forward_middle(self, backend):
        backend.set("TEST", ("a",), "val_a")
        backend.set("TEST", ("b",), "val_b")
        backend.set("TEST", ("c",), "val_c")
        result = backend.order("TEST", ("a",))
        assert result == "b"

    def test_order_forward_last_returns_empty(self, backend):
        backend.set("TEST", ("a",), "val_a")
        backend.set("TEST", ("b",), "val_b")
        result = backend.order("TEST", ("b",))
        assert result == ""

    def test_order_reverse(self, backend):
        backend.set("TEST", ("a",), "val_a")
        backend.set("TEST", ("b",), "val_b")
        backend.set("TEST", ("c",), "val_c")
        result = backend.order("TEST", ("c",), direction=-1)
        assert result == "b"

    def test_order_reverse_last(self, backend):
        """$ORDER(-1, "") returns last subscript."""
        backend.set("TEST", ("a",), "val_a")
        backend.set("TEST", ("b",), "val_b")
        backend.set("TEST", ("c",), "val_c")
        result = backend.order("TEST", ("",), direction=-1)
        assert result == "c"

    def test_order_reverse_first_returns_empty(self, backend):
        backend.set("TEST", ("a",), "val_a")
        backend.set("TEST", ("b",), "val_b")
        result = backend.order("TEST", ("a",), direction=-1)
        assert result == ""

    def test_order_empty_global_returns_empty(self, backend):
        result = backend.order("TEST", ("",))
        assert result == ""

    def test_order_no_subscripts_returns_empty(self, backend):
        result = backend.order("TEST", ())
        assert result == ""

    def test_order_nested_subscripts(self, backend):
        """$ORDER at second level of subscripts."""
        backend.set("TEST", ("1", "a"), "val_a")
        backend.set("TEST", ("1", "b"), "val_b")
        backend.set("TEST", ("1", "c"), "val_c")
        result = backend.order("TEST", ("1", ""))
        assert result == "a"

    def test_order_numeric_collation(self, backend):
        """Numeric subscripts should come before string subscripts."""
        backend.set("TEST", ("1",), "one")
        backend.set("TEST", ("2",), "two")
        backend.set("TEST", ("10",), "ten")
        backend.set("TEST", ("ABC",), "abc")

        # In MUMPS: "" -> 1 -> 2 -> 10 -> "ABC"
        first = backend.order("TEST", ("",))
        assert first == "1"
        second = backend.order("TEST", ("1",))
        assert second == "2"
        third = backend.order("TEST", ("2",))
        assert third == "10"
        fourth = backend.order("TEST", ("10",))
        assert fourth == "ABC"

    def test_order_includes_data_only_nodes(self, backend):
        """$ORDER iterates over nodes even without values (just descendants)."""
        backend.set("TEST", ("1", "a"), "child")
        # Node "1" has no value but has descendants
        result = backend.order("TEST", ("",))
        assert result == "1"

    def test_order_updates_naked_indicator(self, backend):
        backend.set("TEST", ("1",), "one")
        backend.set("TEST", ("2",), "two")
        backend.order("TEST", ("1",))
        naked = backend.get_naked_indicator()
        assert naked is not None
        assert naked[0] == "TEST"


class TestQuery:
    """Test $QUERY (next valued node) operations."""

    def test_query_first_node(self, backend):
        backend.set("TEST", ("1",), "one")
        backend.set("TEST", ("2",), "two")
        result = backend.query("TEST", ("",))
        assert result == "^TEST(1)"

    def test_query_traverses_depth_first(self, backend):
        """$QUERY should traverse depth-first."""
        backend.set("TEST", ("1",), "one")
        backend.set("TEST", ("1", "a"), "one_a")
        backend.set("TEST", ("2",), "two")

        # From ^TEST("") → ^TEST(1) → ^TEST(1,"a") → ^TEST(2)
        r1 = backend.query("TEST", ("",))
        assert r1 == "^TEST(1)"

    def test_query_returns_empty_for_last(self, backend):
        backend.set("TEST", ("1",), "one")
        result = backend.query("TEST", ("1",))
        assert result == ""

    def test_query_empty_global_returns_empty(self, backend):
        result = backend.query("TEST", ("",))
        assert result == ""

    def test_query_skips_valueless_nodes(self, backend):
        """$QUERY only returns nodes that have values."""
        # Node (1) has no value, just a child
        backend.set("TEST", ("1", "a"), "child_val")
        result = backend.query("TEST", ("",))
        assert result == '^TEST(1,"a")'

    def test_query_nested(self, backend):
        backend.set("TEST", ("a", "1"), "v1")
        backend.set("TEST", ("a", "2"), "v2")
        backend.set("TEST", ("b",), "vb")

        r1 = backend.query("TEST", ("",))
        assert r1 == '^TEST("a",1)'
        r2 = backend.query("TEST", ("a", "1"))
        assert r2 == '^TEST("a",2)'
        r3 = backend.query("TEST", ("a", "2"))
        assert r3 == '^TEST("b")'

    def test_query_updates_naked(self, backend):
        backend.set("TEST", ("1",), "one")
        backend.query("TEST", ("",))
        # Naked indicator should be updated
        naked = backend.get_naked_indicator()
        assert naked is not None
