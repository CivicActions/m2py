"""Tests for runtime helper functions.

Tests the helper functions used by generated code for intrinsic functions.
"""

from m2py.runtime import MArray
from m2py.runtime.helpers import (
    _mumps_collation_key,
    m_order,
    m_order_global,
    m_query,
    m_query_global,
)
from m2py.runtime.globals import InMemoryGlobalStorage


class TestMumpsCollationKey:
    """Tests for MUMPS collation order."""

    def test_numeric_ordering(self):
        """Numeric values sort by numeric value."""
        keys = [3, 1, -1, 0, 2, -2]
        sorted_keys = sorted(keys, key=_mumps_collation_key)
        assert sorted_keys == [-2, -1, 0, 1, 2, 3]

    def test_strings_after_numbers(self):
        """Strings sort after all numbers."""
        keys = [1, "A", 0, "B", -1]
        sorted_keys = sorted(keys, key=_mumps_collation_key)
        assert sorted_keys == [-1, 0, 1, "A", "B"]

    def test_numeric_strings_as_numbers(self):
        """Numeric strings are treated as numbers for collation."""
        keys = ["1", "-1", "A", "0"]
        sorted_keys = sorted(keys, key=_mumps_collation_key)
        assert sorted_keys == ["-1", "0", "1", "A"]

    def test_decimal_numbers(self):
        """Decimal numbers sort correctly."""
        keys = ["-1.5", "-1", "-0.5", "0", "0.5", "1"]
        sorted_keys = sorted(keys, key=_mumps_collation_key)
        assert sorted_keys == ["-1.5", "-1", "-0.5", "0", "0.5", "1"]


class TestMOrder:
    """Tests for m_order() helper function."""

    def test_forward_from_empty_string(self):
        """Forward iteration from empty string returns first key."""
        arr = MArray()
        arr[1].value = "a"
        arr[2].value = "b"
        arr[3].value = "c"
        assert m_order(arr, ("",), 1) == "1"

    def test_forward_iteration(self):
        """Forward iteration returns next key."""
        arr = MArray()
        arr[1].value = "a"
        arr[2].value = "b"
        arr[3].value = "c"
        assert m_order(arr, ("1",), 1) == "2"
        assert m_order(arr, ("2",), 1) == "3"
        assert m_order(arr, ("3",), 1) == ""

    def test_reverse_from_empty_string(self):
        """Reverse iteration from empty string returns last key."""
        arr = MArray()
        arr[1].value = "a"
        arr[2].value = "b"
        arr[3].value = "c"
        assert m_order(arr, ("",), -1) == "3"

    def test_reverse_iteration(self):
        """Reverse iteration returns previous key."""
        arr = MArray()
        arr[1].value = "a"
        arr[2].value = "b"
        arr[3].value = "c"
        assert m_order(arr, ("3",), -1) == "2"
        assert m_order(arr, ("2",), -1) == "1"
        assert m_order(arr, ("1",), -1) == ""

    def test_collation_order(self):
        """Keys are returned in MUMPS collation order."""
        arr = MArray()
        arr[-1].value = "neg"
        arr[0].value = "zero"
        arr[1].value = "pos"
        arr["A"].value = "upper"
        arr["a"].value = "lower"
        assert m_order(arr, ("",), 1) == "-1"
        assert m_order(arr, ("1",), 1) == "A"

    def test_none_array(self):
        """None array returns empty string."""
        assert m_order(None, ("",), 1) == ""

    def test_nested_subscripts(self):
        """Nested subscripts work correctly."""
        arr = MArray()
        arr[1, 1].value = "a"
        arr[1, 2].value = "b"
        assert m_order(arr, ("1", ""), 1) == "1"
        assert m_order(arr, ("1", "1"), 1) == "2"


class TestMOrderGlobal:
    """Tests for m_order_global() helper function."""

    def test_forward_iteration(self):
        """Forward iteration on globals works correctly."""
        backend = InMemoryGlobalStorage()
        backend.set("G", ("1",), "a")
        backend.set("G", ("2",), "b")
        backend.set("G", ("3",), "c")
        assert m_order_global(backend, "G", ("",), 1) == "1"
        assert m_order_global(backend, "G", ("1",), 1) == "2"


class TestMQuery:
    """Tests for m_query() helper function."""

    def test_depth_first_traversal(self):
        """Query traverses tree depth-first."""
        arr = MArray()
        arr[1, 1].value = 1
        arr[1, 2].value = 2
        arr[2, 1].value = 3
        assert m_query(arr, "A", ("",)) == "A(1,1)"
        assert m_query(arr, "A", ("1", "1")) == "A(1,2)"
        assert m_query(arr, "A", ("1", "2")) == "A(2,1)"
        assert m_query(arr, "A", ("2", "1")) == ""

    def test_varying_depth(self):
        """Query handles varying depth correctly."""
        arr = MArray()
        arr[1, 1, 1].value = 1
        arr[1, 2].value = 2
        arr[2].value = 3
        assert m_query(arr, "A", ("",)) == "A(1,1,1)"
        assert m_query(arr, "A", ("1", "1", "1")) == "A(1,2)"
        assert m_query(arr, "A", ("1", "2")) == "A(2)"
        assert m_query(arr, "A", ("2",)) == ""

    def test_none_array(self):
        """None array returns empty string."""
        assert m_query(None, "A", ("",)) == ""


class TestMQueryGlobal:
    """Tests for m_query_global() helper function."""

    def test_basic_traversal(self):
        """Query on globals traverses correctly."""
        backend = InMemoryGlobalStorage()
        backend.set("G", ("1", "1"), "a")
        backend.set("G", ("1", "2"), "b")
        assert m_query_global(backend, "G", ("",)) == "^G(1,1)"
        assert m_query_global(backend, "G", ("1", "1")) == "^G(1,2)"
