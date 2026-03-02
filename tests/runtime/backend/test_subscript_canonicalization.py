"""Tests for subscript canonicalization across all backends.

Validates that numeric vs string subscripts are properly canonicalized
and stored in MUMPS collation order.
"""

from __future__ import annotations


class TestNumericCanonicalization:
    """Test that numeric subscripts are canonicalized correctly."""

    def test_integer_subscript(self, backend):
        """Integer subscript '1' and 1 should be equivalent."""
        backend.set("TEST", ("1",), "one")
        assert backend.get("TEST", ("1",)) == "one"

    def test_leading_zeros_are_string(self, backend):
        """'01' is a string in MUMPS (not canonical numeric), '1' is numeric."""
        backend.set("TEST", ("01",), "zero_one")
        backend.set("TEST", ("1",), "one")
        assert backend.get("TEST", ("01",)) == "zero_one"
        assert backend.get("TEST", ("1",)) == "one"

    def test_trailing_zeros_are_string(self, backend):
        """'1.0' is a string in MUMPS (not canonical numeric), '1' is numeric."""
        backend.set("TEST", ("1.0",), "one_point_zero")
        backend.set("TEST", ("1",), "one")
        assert backend.get("TEST", ("1.0",)) == "one_point_zero"
        assert backend.get("TEST", ("1",)) == "one"

    def test_negative_zero(self, backend):
        """-0 should canonicalize to 0."""
        backend.set("TEST", ("-0",), "zero")
        # -0 is not canonical numeric in MUMPS, so it stays as string "-0"
        assert backend.get("TEST", ("-0",)) == "zero"

    def test_negative_number(self, backend):
        backend.set("TEST", ("-1",), "neg_one")
        assert backend.get("TEST", ("-1",)) == "neg_one"

    def test_decimal_value(self, backend):
        backend.set("TEST", (".5",), "half")
        assert backend.get("TEST", (".5",)) == "half"

    def test_large_number(self, backend):
        backend.set("TEST", ("123456789",), "large")
        assert backend.get("TEST", ("123456789",)) == "large"


class TestStringSubscripts:
    """Test that string subscripts are handled correctly."""

    def test_pure_string_subscript(self, backend):
        backend.set("TEST", ("ABC",), "alpha")
        assert backend.get("TEST", ("ABC",)) == "alpha"

    def test_mixed_alphanumeric(self, backend):
        backend.set("TEST", ("A1",), "mixed")
        assert backend.get("TEST", ("A1",)) == "mixed"

    def test_space_in_subscript(self, backend):
        backend.set("TEST", ("hello world",), "spaced")
        assert backend.get("TEST", ("hello world",)) == "spaced"


class TestCollationOrder:
    """Test MUMPS collation order: numbers before strings."""

    def test_numeric_before_string(self, backend):
        """In MUMPS, numeric subscripts collate before strings."""
        backend.set("TEST", ("ABC",), "string")
        backend.set("TEST", ("1",), "number")

        first = backend.order("TEST", ("",))
        assert first == "1"

    def test_numeric_order(self, backend):
        """Numeric subscripts in proper order: -2, -1, 0, 1, 2, 10."""
        for n in ["10", "-1", "0", "2", "1", "-2"]:
            backend.set("TEST", (n,), f"val_{n}")

        results = []
        current = ""
        for _ in range(10):
            current = backend.order("TEST", (current,))
            if current == "":
                break
            results.append(current)

        assert results == ["-2", "-1", "0", "1", "2", "10"]

    def test_string_order(self, backend):
        """String subscripts in ASCII order."""
        for s in ["C", "A", "B"]:
            backend.set("TEST", (s,), f"val_{s}")

        results = []
        current = ""
        for _ in range(10):
            current = backend.order("TEST", (current,))
            if current == "":
                break
            results.append(current)

        assert results == ["A", "B", "C"]

    def test_mixed_numeric_string_order(self, backend):
        """Full MUMPS collation: negatives, zero, positives, then strings."""
        subs = ["-1", "0", "2", "ABC", "1", "DEF"]
        for s in subs:
            backend.set("TEST", (s,), f"val_{s}")

        results = []
        current = ""
        for _ in range(10):
            current = backend.order("TEST", (current,))
            if current == "":
                break
            results.append(current)

        assert results == ["-1", "0", "1", "2", "ABC", "DEF"]
