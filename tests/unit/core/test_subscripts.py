"""Unit tests for SubscriptCanonicalizer.

Tests subscript value canonicalization per MUMPS rules and
contracts/subscript-canonicalizer.md.

Feature: 018-unified-variable-system
Requirements: FR-003, FR-004
"""

from decimal import Decimal

from m2py.core.subscripts import SubscriptCanonicalizer


class TestCanonicalize:
    """Tests for SubscriptCanonicalizer.canonicalize()"""

    def test_integer(self):
        """Integer values are stringified."""
        assert SubscriptCanonicalizer.canonicalize(1) == "1"
        assert SubscriptCanonicalizer.canonicalize(0) == "0"
        assert SubscriptCanonicalizer.canonicalize(99) == "99"
        assert SubscriptCanonicalizer.canonicalize(-1) == "-1"

    def test_numeric_literal_with_leading_zero(self):
        """Python numeric literal 01 is just 1, so canonicalizes to "1"."""
        # Note: In Python 3, 01 is a syntax error, but 0o1 is octal 1
        # The MUMPS 01 literal is handled at parse time in MUMPS
        # When we receive a Python int, it's already normalized
        assert SubscriptCanonicalizer.canonicalize(1) == "1"

    def test_float_equal_to_int(self):
        """Floats equal to integers canonicalize as integers."""
        assert SubscriptCanonicalizer.canonicalize(1.0) == "1"
        assert SubscriptCanonicalizer.canonicalize(5.0) == "5"
        assert SubscriptCanonicalizer.canonicalize(-3.0) == "-3"
        assert SubscriptCanonicalizer.canonicalize(0.0) == "0"

    def test_float_with_fractional(self):
        """Floats with fractional parts have trailing zeros removed."""
        assert SubscriptCanonicalizer.canonicalize(1.5) == "1.5"
        assert SubscriptCanonicalizer.canonicalize(1.50) == "1.5"
        assert SubscriptCanonicalizer.canonicalize(1.500) == "1.5"
        assert SubscriptCanonicalizer.canonicalize(2.25) == "2.25"

    def test_float_less_than_one(self):
        """Floats less than 1 have no leading zero."""
        assert SubscriptCanonicalizer.canonicalize(0.5) == ".5"
        assert SubscriptCanonicalizer.canonicalize(0.25) == ".25"
        assert SubscriptCanonicalizer.canonicalize(0.125) == ".125"

    def test_negative_float_less_than_one(self):
        """Negative floats less than 1 in absolute value."""
        assert SubscriptCanonicalizer.canonicalize(-0.5) == "-.5"
        assert SubscriptCanonicalizer.canonicalize(-0.25) == "-.25"

    def test_string_canonical_numeric(self):
        """Canonical numeric strings stay the same."""
        assert SubscriptCanonicalizer.canonicalize("1") == "1"
        assert SubscriptCanonicalizer.canonicalize("1.5") == "1.5"
        assert SubscriptCanonicalizer.canonicalize(".5") == ".5"
        assert SubscriptCanonicalizer.canonicalize("-1") == "-1"

    def test_string_non_canonical_numeric_preserved(self):
        """Non-canonical numeric strings are PRESERVED (not converted)."""
        # This is the key behavior - "01" is NOT the same as 1
        assert SubscriptCanonicalizer.canonicalize("01") == "01"
        assert SubscriptCanonicalizer.canonicalize("001") == "001"
        assert SubscriptCanonicalizer.canonicalize("1.0") == "1.0"
        assert SubscriptCanonicalizer.canonicalize("1.50") == "1.50"
        assert SubscriptCanonicalizer.canonicalize("0.5") == "0.5"  # Has leading zero

    def test_string_non_numeric_preserved(self):
        """Non-numeric strings are preserved exactly."""
        assert SubscriptCanonicalizer.canonicalize("1X") == "1X"
        assert SubscriptCanonicalizer.canonicalize("ABC") == "ABC"
        assert SubscriptCanonicalizer.canonicalize("hello") == "hello"
        assert SubscriptCanonicalizer.canonicalize("") == ""
        assert SubscriptCanonicalizer.canonicalize("  ") == "  "

    def test_marray_value_extraction(self):
        """Objects with .value attribute have value extracted."""

        class MockMArray:
            def __init__(self, v):
                self.value = v

        assert SubscriptCanonicalizer.canonicalize(MockMArray(1)) == "1"
        assert SubscriptCanonicalizer.canonicalize(MockMArray("01")) == "01"
        assert SubscriptCanonicalizer.canonicalize(MockMArray("test")) == "test"

    def test_decimal_equal_to_int(self):
        """Decimal values equal to integers canonicalize as integers."""
        assert SubscriptCanonicalizer.canonicalize(Decimal("1.0")) == "1"
        assert SubscriptCanonicalizer.canonicalize(Decimal("1.00")) == "1"
        assert SubscriptCanonicalizer.canonicalize(Decimal("5.0")) == "5"
        assert SubscriptCanonicalizer.canonicalize(Decimal("-3.0")) == "-3"

    def test_decimal_with_fractional(self):
        """Decimal values with fractional parts."""
        assert SubscriptCanonicalizer.canonicalize(Decimal("1.5")) == "1.5"
        assert SubscriptCanonicalizer.canonicalize(Decimal("0.5")) == ".5"
        assert SubscriptCanonicalizer.canonicalize(Decimal("-0.5")) == "-.5"


class TestCanonicalizeNumeric:
    """Tests for SubscriptCanonicalizer.canonicalize_numeric()"""

    def test_integers(self):
        """Integer canonicalization."""
        assert SubscriptCanonicalizer.canonicalize_numeric(1) == "1"
        assert SubscriptCanonicalizer.canonicalize_numeric(0) == "0"
        assert SubscriptCanonicalizer.canonicalize_numeric(123) == "123"
        assert SubscriptCanonicalizer.canonicalize_numeric(-42) == "-42"

    def test_floats_equal_to_int(self):
        """Float equal to int canonicalizes as int."""
        assert SubscriptCanonicalizer.canonicalize_numeric(1.0) == "1"
        assert SubscriptCanonicalizer.canonicalize_numeric(0.0) == "0"
        assert SubscriptCanonicalizer.canonicalize_numeric(-5.0) == "-5"

    def test_floats_with_decimal(self):
        """Float with decimal part."""
        assert SubscriptCanonicalizer.canonicalize_numeric(1.5) == "1.5"
        assert SubscriptCanonicalizer.canonicalize_numeric(2.25) == "2.25"
        assert SubscriptCanonicalizer.canonicalize_numeric(-3.14159) == "-3.14159"

    def test_floats_trailing_zeros_removed(self):
        """Trailing zeros are removed."""
        assert SubscriptCanonicalizer.canonicalize_numeric(1.50) == "1.5"
        assert SubscriptCanonicalizer.canonicalize_numeric(2.500) == "2.5"

    def test_floats_less_than_one(self):
        """Values less than 1 have no leading zero."""
        assert SubscriptCanonicalizer.canonicalize_numeric(0.5) == ".5"
        assert SubscriptCanonicalizer.canonicalize_numeric(0.1) == ".1"
        assert SubscriptCanonicalizer.canonicalize_numeric(0.123) == ".123"

    def test_negative_floats_less_than_one(self):
        """Negative values less than 1 in absolute value."""
        assert SubscriptCanonicalizer.canonicalize_numeric(-0.5) == "-.5"
        assert SubscriptCanonicalizer.canonicalize_numeric(-0.1) == "-.1"


class TestIsCanonicalNumericString:
    """Tests for SubscriptCanonicalizer.is_canonical_numeric_string()"""

    def test_canonical_integers(self):
        """Integer strings in canonical form."""
        assert SubscriptCanonicalizer.is_canonical_numeric_string("1")
        assert SubscriptCanonicalizer.is_canonical_numeric_string("0")
        assert SubscriptCanonicalizer.is_canonical_numeric_string("123")
        assert SubscriptCanonicalizer.is_canonical_numeric_string("-42")

    def test_canonical_floats(self):
        """Float strings in canonical form."""
        assert SubscriptCanonicalizer.is_canonical_numeric_string("1.5")
        assert SubscriptCanonicalizer.is_canonical_numeric_string(".5")
        assert SubscriptCanonicalizer.is_canonical_numeric_string("-.5")
        assert SubscriptCanonicalizer.is_canonical_numeric_string("-1.5")

    def test_non_canonical_leading_zero(self):
        """Leading zero makes non-canonical."""
        assert not SubscriptCanonicalizer.is_canonical_numeric_string("01")
        assert not SubscriptCanonicalizer.is_canonical_numeric_string("001")
        assert not SubscriptCanonicalizer.is_canonical_numeric_string(
            "0.5"
        )  # Should be .5

    def test_non_canonical_trailing_zero(self):
        """Trailing zero after decimal makes non-canonical."""
        assert not SubscriptCanonicalizer.is_canonical_numeric_string("1.0")
        assert not SubscriptCanonicalizer.is_canonical_numeric_string("1.50")
        assert not SubscriptCanonicalizer.is_canonical_numeric_string("2.500")

    def test_non_canonical_trailing_dot(self):
        """Trailing decimal point makes non-canonical.

        YDB verified: '-4.' is NOT canonical (canonical is '-4').
        This was a bug fix - trailing dots are NOT valid canonical numbers.
        """
        assert not SubscriptCanonicalizer.is_canonical_numeric_string("-4.")
        assert not SubscriptCanonicalizer.is_canonical_numeric_string("4.")
        assert not SubscriptCanonicalizer.is_canonical_numeric_string("0.")
        assert not SubscriptCanonicalizer.is_canonical_numeric_string(".")

    def test_canonical_negative_decimals(self):
        """Negative decimals in canonical form."""
        # -.5 is canonical, -0.5 is not
        assert SubscriptCanonicalizer.is_canonical_numeric_string("-.5")
        assert SubscriptCanonicalizer.is_canonical_numeric_string("-1.5")
        assert not SubscriptCanonicalizer.is_canonical_numeric_string("-0.5")

    def test_canonical_positive_decimals(self):
        """Positive decimals in canonical form."""
        # .5 is canonical, 0.5 is not
        assert SubscriptCanonicalizer.is_canonical_numeric_string(".5")
        assert SubscriptCanonicalizer.is_canonical_numeric_string("1.5")
        assert not SubscriptCanonicalizer.is_canonical_numeric_string("0.5")

    def test_non_numeric(self):
        """Non-numeric strings return False."""
        assert not SubscriptCanonicalizer.is_canonical_numeric_string("1X")
        assert not SubscriptCanonicalizer.is_canonical_numeric_string("ABC")
        assert not SubscriptCanonicalizer.is_canonical_numeric_string("hello")
        assert not SubscriptCanonicalizer.is_canonical_numeric_string("1+1")

    def test_empty_string(self):
        """Empty string is not canonical numeric."""
        assert not SubscriptCanonicalizer.is_canonical_numeric_string("")

    def test_whitespace(self):
        """Whitespace is not canonical numeric."""
        assert not SubscriptCanonicalizer.is_canonical_numeric_string("  ")
        assert not SubscriptCanonicalizer.is_canonical_numeric_string(" 1")


class TestSubscriptsEqual:
    """Tests for SubscriptCanonicalizer.subscripts_equal()"""

    def test_int_and_canonical_string(self):
        """Integer and its string representation are equal."""
        assert SubscriptCanonicalizer.subscripts_equal(1, "1")
        assert SubscriptCanonicalizer.subscripts_equal(0, "0")
        assert SubscriptCanonicalizer.subscripts_equal(123, "123")

    def test_int_and_non_canonical_string(self):
        """Integer and non-canonical string are NOT equal."""
        assert not SubscriptCanonicalizer.subscripts_equal(1, "01")
        assert not SubscriptCanonicalizer.subscripts_equal(1, "001")
        assert not SubscriptCanonicalizer.subscripts_equal(1, "1.0")

    def test_float_and_int(self):
        """Float equal to int and int are equal."""
        assert SubscriptCanonicalizer.subscripts_equal(1.0, 1)
        assert SubscriptCanonicalizer.subscripts_equal(5.0, 5)

    def test_same_strings(self):
        """Identical strings are equal."""
        assert SubscriptCanonicalizer.subscripts_equal("ABC", "ABC")
        assert SubscriptCanonicalizer.subscripts_equal("01", "01")

    def test_different_strings(self):
        """Different strings are not equal."""
        assert not SubscriptCanonicalizer.subscripts_equal("ABC", "DEF")
        assert not SubscriptCanonicalizer.subscripts_equal("1", "01")


class TestYDBVerifiedBehavior:
    """Tests based on YDB verification from research.md."""

    def test_one_and_string_one_same_node(self):
        """A(1) and A("1") access the same node (YDB verified)."""
        # Both canonicalize to "1"
        assert SubscriptCanonicalizer.canonicalize(1) == "1"
        assert SubscriptCanonicalizer.canonicalize("1") == "1"
        assert SubscriptCanonicalizer.subscripts_equal(1, "1")

    def test_one_and_string_01_different_nodes(self):
        """A(1) and A("01") access DIFFERENT nodes (YDB verified)."""
        assert SubscriptCanonicalizer.canonicalize(1) == "1"
        assert SubscriptCanonicalizer.canonicalize("01") == "01"
        assert not SubscriptCanonicalizer.subscripts_equal(1, "01")

    def test_numeric_literal_01_same_as_1(self):
        """A(01) numeric literal is same as A(1) (YDB verified).

        Note: In MUMPS, 01 the numeric literal canonicalizes to 1 at parse time.
        In Python, we receive the already-parsed value as int 1.
        """
        # When codegen parses MUMPS "01" as numeric, it becomes Python int 1
        assert SubscriptCanonicalizer.canonicalize(1) == "1"


class TestMugjPatterns:
    """Tests based on MUGJ test patterns."""

    def test_subscript_patterns_from_vv2vnia(self):
        """Subscript patterns from VV2VNIA indirection tests."""
        # Simple integer subscripts
        assert SubscriptCanonicalizer.canonicalize(1) == "1"
        assert SubscriptCanonicalizer.canonicalize(2) == "2"
        assert SubscriptCanonicalizer.canonicalize(3) == "3"

        # Multiple subscripts for nested access
        subs = [1, 2, 3]
        canonical = [SubscriptCanonicalizer.canonicalize(s) for s in subs]
        assert canonical == ["1", "2", "3"]

    def test_string_subscript_preservation(self):
        """String subscripts from dynamic indirection are preserved."""
        # When @A evaluates to "01", that exact string is used as subscript
        assert SubscriptCanonicalizer.canonicalize("01") == "01"
        assert SubscriptCanonicalizer.canonicalize("A") == "A"
        assert (
            SubscriptCanonicalizer.canonicalize("B(3,4)") == "B(3,4)"
        )  # Nested ref as string


class TestDecimalPrecisionInCanonical:
    """Tests for Decimal precision in is_canonical_numeric_string().

    The fix changed float() to Decimal() in is_canonical_numeric_string()
    because float loses precision for very small numbers, causing
    -.0000000001 to be misidentified.

    Fixed suite: V4SORT (test 40079)
    """

    def test_very_small_negative_decimal(self):
        """Very small negative decimals must be recognized as canonical.

        -.0000000001 is a canonical numeric string — float() would lose
        precision and return a wrong canonical form, but Decimal() handles it.
        """
        assert SubscriptCanonicalizer.is_canonical_numeric_string("-.0000000001")

    def test_very_small_positive_decimal(self):
        """Very small positive decimals must be recognized as canonical."""
        assert SubscriptCanonicalizer.is_canonical_numeric_string(".0000000001")

    def test_precision_boundary(self):
        """Numbers at float precision boundary are still canonical."""
        assert SubscriptCanonicalizer.is_canonical_numeric_string("-.00000000000000001")
        assert SubscriptCanonicalizer.is_canonical_numeric_string(".00000000000000001")

    def test_non_canonical_small_decimal(self):
        """Non-canonical forms with leading zero are still rejected."""
        assert not SubscriptCanonicalizer.is_canonical_numeric_string("-0.0000000001")
        assert not SubscriptCanonicalizer.is_canonical_numeric_string("0.0000000001")
