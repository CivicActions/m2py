"""Unit tests for m2py.core.values — MUMPS value semantics.

Tests the canonical source-of-truth implementations for MUMPS value model
functions introduced in feature 019-foundation-cleanup.

Semantics verified against YottaDB (Docker):
    echo 'TEST W +.50,!,1E-44,!,1E-43,!,...' | docker run --rm -i ydb
"""

from decimal import Decimal

import pytest

from m2py.core.values import (
    _decimal_binop,
    m_add,
    m_compare,
    m_mul,
    m_num,
    m_str,
    m_sub,
    m_truth,
    mumps_canonical_str,
)


# =============================================================================
# mumps_canonical_str
# =============================================================================


class TestMumpsCanonicalStr:
    """Tests for mumps_canonical_str — numeric → MUMPS canonical string."""

    # --- Integers ---

    def test_zero(self):
        assert mumps_canonical_str(0) == "0"

    def test_positive_int(self):
        assert mumps_canonical_str(42) == "42"

    def test_negative_int(self):
        assert mumps_canonical_str(-42) == "-42"

    def test_large_int(self):
        assert mumps_canonical_str(12345678901234567890) == "12345678901234567890"

    # --- Floats ---

    def test_float_integer_equivalent(self):
        """Float that equals int → no decimal point."""
        assert mumps_canonical_str(3.0) == "3"

    def test_float_with_fraction(self):
        assert mumps_canonical_str(3.14) == "3.14"

    def test_float_leading_zero_removed(self):
        """YDB: +.50 → .5"""
        assert mumps_canonical_str(0.5) == ".5"

    def test_float_negative_leading_zero_removed(self):
        """YDB: -.5 → -.5"""
        assert mumps_canonical_str(-0.5) == "-.5"

    def test_float_trailing_zeros_removed(self):
        """YDB: 3.140 → 3.14"""
        assert mumps_canonical_str(3.140) == "3.14"

    def test_float_zero(self):
        assert mumps_canonical_str(0.0) == "0"

    def test_float_negative_zero(self):
        assert mumps_canonical_str(-0.0) == "0"

    def test_float_small(self):
        """YDB: 7e-15 → .000000000000007"""
        assert mumps_canonical_str(7e-15) == ".000000000000007"

    def test_float_large(self):
        """YDB: 7E15 → 7000000000000000"""
        assert mumps_canonical_str(7e15) == "7000000000000000"

    # --- Decimals ---

    def test_decimal_zero(self):
        assert mumps_canonical_str(Decimal("0")) == "0"

    def test_decimal_integer(self):
        assert mumps_canonical_str(Decimal("42")) == "42"

    def test_decimal_fraction(self):
        assert mumps_canonical_str(Decimal("3.14")) == "3.14"

    def test_decimal_leading_zero_removed(self):
        assert mumps_canonical_str(Decimal("0.5")) == ".5"

    def test_decimal_trailing_zeros_removed(self):
        assert mumps_canonical_str(Decimal("3.140")) == "3.14"

    def test_decimal_negative(self):
        assert mumps_canonical_str(Decimal("-3.14")) == "-3.14"

    def test_decimal_negative_fraction(self):
        assert mumps_canonical_str(Decimal("-0.5")) == "-.5"

    # --- Exponent guard (YDB behaviour) ---

    def test_exponent_guard_below_threshold(self):
        """YDB: 1E-44 → 0"""
        assert mumps_canonical_str(Decimal("1E-44")) == "0"

    def test_exponent_guard_at_threshold(self):
        """YDB: 1E-43 → .0000000000000000000000000000000000000000001"""
        result = mumps_canonical_str(Decimal("1E-43"))
        assert result == ".0000000000000000000000000000000000000000001"

    def test_exponent_guard_extreme(self):
        """Very small exponents should return '0'."""
        assert mumps_canonical_str(Decimal("1E-100")) == "0"

    # --- Decimal with trailing zeros (normalize fix) ---

    def test_decimal_trailing_zeros_in_significant_digits(self):
        """Decimal with many trailing zeros should normalize correctly.

        This was a regression: Decimal("0.123000...000") had raw exponent -51,
        tripping the exponent guard. normalize() fixes this.
        """
        val = Decimal("00000.123000000000000000000000000000000000000000000000000")
        assert mumps_canonical_str(val) == ".123"

    def test_decimal_long_precision_preserved(self):
        """Long decimal precision must be preserved across normalize().

        Default Decimal precision is 28; normalize() must use higher precision.
        """
        assert (
            mumps_canonical_str(Decimal(".12345678901234567890123456789"))
            == ".12345678901234567890123456789"
        )

    def test_decimal_negative_long_precision(self):
        assert (
            mumps_canonical_str(Decimal("-.12345678901234567890123456789"))
            == "-.12345678901234567890123456789"
        )

    # --- Scientific notation expansion ---

    def test_decimal_scientific_positive_exponent(self):
        """YDB: 1E2 → 100"""
        assert mumps_canonical_str(Decimal("1E2")) == "100"

    def test_decimal_scientific_large(self):
        assert mumps_canonical_str(Decimal("1.5E3")) == "1500"

    # --- Infinity / NaN ---

    def test_decimal_infinity(self):
        assert mumps_canonical_str(Decimal("Infinity")) == "0"

    def test_decimal_nan(self):
        assert mumps_canonical_str(Decimal("NaN")) == "0"


# =============================================================================
# m_str
# =============================================================================


class TestMStr:
    """Tests for m_str — any value → MUMPS string."""

    def test_string_passthrough(self):
        assert m_str("hello") == "hello"

    def test_int(self):
        assert m_str(42) == "42"

    def test_float(self):
        assert m_str(3.14) == "3.14"

    def test_float_zero(self):
        assert m_str(0.0) == "0"

    def test_decimal(self):
        assert m_str(Decimal("3.14")) == "3.14"

    def test_decimal_leading_zero(self):
        assert m_str(Decimal("0.5")) == ".5"

    def test_none(self):
        """None → empty string (via str())."""
        assert m_str(None) == "None"

    def test_marray_unwrap(self):
        """MArray-like objects are unwrapped."""

        class FakeMArray:
            value = 42

        assert m_str(FakeMArray()) == "42"

    def test_float_small(self):
        assert m_str(7e-15) == ".000000000000007"


# =============================================================================
# m_num
# =============================================================================


class TestMNum:
    """Tests for m_num — MUMPS numeric coercion (ANSI §7.1.4.5)."""

    # --- Already numeric ---

    def test_int(self):
        assert m_num(3) == 3

    def test_float_integer_equivalent(self):
        """Float 3.0 → normalised to int 3."""
        assert m_num(3.0) == 3
        assert isinstance(m_num(3.0), int)

    def test_float_fractional(self):
        assert m_num(3.14) == 3.14

    def test_decimal_integer_equivalent(self):
        assert m_num(Decimal("3.0")) == 3
        assert isinstance(m_num(Decimal("3.0")), int)

    def test_decimal_fractional(self):
        assert m_num(Decimal("3.14")) == Decimal("3.14")

    # --- String coercion ---

    def test_numeric_string(self):
        assert m_num("42") == 42

    def test_leading_text_stops_parse(self):
        """YDB: "A3"+0 → 0"""
        assert m_num("A3") == 0

    def test_trailing_text_ignored(self):
        """YDB: "3A"+0 → 3"""
        assert m_num("3A") == 3

    def test_leading_whitespace_stops(self):
        """YDB: " 42"+0 → 0 (space is not a sign character!)"""
        assert m_num(" 42") == 0

    def test_empty_string(self):
        assert m_num("") == 0

    def test_pure_text(self):
        assert m_num("hello") == 0

    # --- Sign composition ---

    def test_plus_minus(self):
        """YDB: "+-5"+0 → -5"""
        assert m_num("+-5") == -5

    def test_minus_minus(self):
        """YDB: "--5"+0 → 5"""
        assert m_num("--5") == 5

    def test_plus_plus(self):
        assert m_num("++5") == 5

    def test_minus_plus(self):
        assert m_num("-+5") == -5

    # --- Scientific notation (uppercase E only) ---

    def test_scientific_notation(self):
        """YDB: 1E2 → 100"""
        assert m_num("1E2") == 100

    def test_scientific_lowercase_not_parsed(self):
        """Lowercase 'e' is NOT scientific notation in MUMPS."""
        assert m_num("1e2") == 1

    def test_scientific_negative_exponent(self):
        result = m_num("1E-2")
        assert result == Decimal("0.01")

    # --- MArray unwrap ---

    def test_marray_unwrap(self):
        class FakeMArray:
            value = "42"

        assert m_num(FakeMArray()) == 42

    # --- Decimal point only ---

    def test_lone_decimal(self):
        assert m_num(".") == 0

    def test_decimal_no_integer_part(self):
        assert m_num(".5") == Decimal("0.5")


# =============================================================================
# m_truth
# =============================================================================


class TestMTruth:
    """Tests for m_truth — MUMPS truth value (ANSI §1.2.4)."""

    def test_zero_is_false(self):
        assert m_truth(0) is False

    def test_nonzero_is_true(self):
        assert m_truth(1) is True

    def test_negative_is_true(self):
        assert m_truth(-1) is True

    def test_string_zero_is_false(self):
        assert m_truth("0") is False

    def test_string_nonzero_is_true(self):
        assert m_truth("1") is True

    def test_non_numeric_string_is_false(self):
        """Non-numeric string → m_num → 0 → False."""
        assert m_truth("hello") is False

    def test_empty_string_is_false(self):
        assert m_truth("") is False

    def test_float_zero_is_false(self):
        assert m_truth(0.0) is False

    def test_decimal_zero_is_false(self):
        assert m_truth(Decimal("0")) is False


# =============================================================================
# m_compare
# =============================================================================


class TestMCompare:
    """Tests for m_compare — MUMPS comparison operators."""

    # --- Equality (string-based) ---

    def test_equal_integers(self):
        assert m_compare(3, "=", 3) == 1

    def test_not_equal_integers(self):
        assert m_compare(3, "=", 4) == 0

    def test_string_vs_numeric_equality(self):
        """YDB: "3.0"=3 → 0  (string "3.0" ≠ canonical "3")."""
        assert m_compare("3.0", "=", 3) == 0

    def test_numeric_equality_canonicalized(self):
        """3.0 (float) = 3 (int) → 1 because both canonicalize to "3"."""
        assert m_compare(3.0, "=", 3) == 1

    def test_string_equality(self):
        assert m_compare("hello", "=", "hello") == 1

    def test_string_inequality(self):
        assert m_compare("hello", "=", "world") == 0

    # --- Less-than (numeric) ---

    def test_less_than_true(self):
        assert m_compare(2, "<", 3) == 1

    def test_less_than_false(self):
        assert m_compare(3, "<", 2) == 0

    def test_less_than_equal(self):
        assert m_compare(3, "<", 3) == 0

    # --- Greater-than (numeric) ---

    def test_greater_than_true(self):
        assert m_compare(3, ">", 2) == 1

    def test_greater_than_false(self):
        assert m_compare(2, ">", 3) == 0

    # --- MArray unwrap ---

    def test_marray_unwrap_equality(self):
        class FakeMArray:
            value = 42

        assert m_compare(FakeMArray(), "=", 42) == 1

    # --- Invalid operator ---

    def test_invalid_operator(self):
        with pytest.raises(ValueError, match="Unknown MUMPS comparison operator"):
            m_compare(1, "?", 2)


# =============================================================================
# _decimal_binop / m_add / m_sub / m_mul
# =============================================================================


class TestDecimalBinop:
    """Tests for 18-digit precision arithmetic helpers."""

    def test_add_integers(self):
        assert m_add(2, 3) == 5

    def test_add_returns_int_when_whole(self):
        result = m_add(1, 2)
        assert isinstance(result, int)

    def test_add_decimals(self):
        result = m_add("1.1", "2.2")
        assert result == Decimal("3.3")

    def test_add_mixed_types(self):
        assert m_add("3", 4) == 7

    def test_sub_basic(self):
        assert m_sub(5, 3) == 2

    def test_sub_negative_result(self):
        assert m_sub(3, 5) == -2

    def test_sub_returns_int_when_whole(self):
        result = m_sub(5, 3)
        assert isinstance(result, int)

    def test_mul_basic(self):
        assert m_mul(3, 4) == 12

    def test_mul_decimal(self):
        result = m_mul("1.5", "2")
        assert result == 3

    def test_mul_returns_int_when_whole(self):
        result = m_mul(3, 4)
        assert isinstance(result, int)

    def test_decimal_binop_invalid_op(self):
        with pytest.raises(ValueError, match="Unsupported op"):
            _decimal_binop(1, 2, "/")

    def test_precision_18_digits(self):
        """Verify 18-digit precision."""
        result = m_add(Decimal("0.123456789012345678"), Decimal("0"))
        # Should preserve 18 significant digits
        assert result == Decimal("0.123456789012345678")
