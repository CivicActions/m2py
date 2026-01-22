"""Tests for code generation helper functions.

Tests the helper functions used by generated code to implement MUMPS semantics.

Reference: ANSI MUMPS 7.1.4.5 (numeric coercion), 1.2.4 (truth values)
"""

import pytest

from m2py.codegen.helpers import m_compare, m_num, m_truth


@pytest.mark.codegen
class TestMNum:
    """Tests for m_num() - MUMPS numeric coercion (§7.1.4.5)."""

    def test_integer_passthrough(self):
        """Integer values pass through unchanged."""
        assert m_num(0) == 0
        assert m_num(1) == 1
        assert m_num(-1) == -1
        assert m_num(42) == 42

    def test_float_normalization(self):
        """Float values normalize to int when they represent whole numbers."""
        assert m_num(0.0) == 0
        assert m_num(1.0) == 1
        assert m_num(3.0) == 3
        assert m_num(-5.0) == -5
        assert isinstance(m_num(3.0), int)
        assert isinstance(m_num(0.0), int)

    def test_float_with_decimal_preserved(self):
        """Float values with fractional parts are preserved as float."""
        assert m_num(3.14) == 3.14
        assert m_num(0.5) == 0.5
        assert m_num(-2.7) == -2.7
        assert isinstance(m_num(3.14), float)

    def test_numeric_string_integer(self):
        """Numeric strings convert to integers."""
        assert m_num("3") == 3
        assert m_num("42") == 42
        assert m_num("-1") == -1
        assert isinstance(m_num("3"), int)

    def test_numeric_string_float(self):
        """Numeric strings with decimals convert to float or int."""
        assert m_num("3.14") == 3.14
        assert m_num("3.0") == 3  # Normalized to int
        assert m_num("0.5") == 0.5
        assert isinstance(m_num("3.14"), float)
        assert isinstance(m_num("3.0"), int)

    def test_leading_zeros_stripped(self):
        """Leading zeros are stripped per MUMPS canonical form."""
        assert m_num("007") == 7
        assert m_num("0042") == 42
        assert m_num("00.5") == 0.5

    def test_leading_whitespace_stripped(self):
        """Leading whitespace is stripped per §7.1.4.5."""
        assert m_num("  42") == 42
        assert m_num("\t5") == 5
        assert m_num("   -3") == -3

    def test_trailing_non_numeric_ignored(self):
        """Trailing non-numeric characters are ignored."""
        assert m_num("3A") == 3
        assert m_num("42XYZ") == 42
        assert m_num("3.14ABC") == 3.14

    def test_non_numeric_prefix_returns_zero(self):
        """Strings without numeric prefix return 0."""
        assert m_num("A3") == 0
        assert m_num("ABC") == 0
        assert m_num("XYZ") == 0

    def test_empty_string_returns_zero(self):
        """Empty string returns 0."""
        assert m_num("") == 0

    def test_sign_processing(self):
        """Multiple leading signs are processed correctly."""
        assert m_num("+5") == 5
        assert m_num("-5") == -5
        assert m_num("+-5") == -5  # + then - = negative
        assert m_num("-+5") == -5  # - then + = negative
        assert m_num("--5") == 5  # - then - = positive
        assert m_num("++5") == 5  # + then + = positive

    def test_sign_only_returns_zero(self):
        """Sign characters without digits return 0."""
        assert m_num("+") == 0
        assert m_num("-") == 0
        assert m_num("+-") == 0

    def test_decimal_point_only_returns_zero(self):
        """Decimal point without digits returns 0."""
        assert m_num(".") == 0
        assert m_num("+.") == 0
        assert m_num("-.") == 0


@pytest.mark.codegen
class TestMTruth:
    """Tests for m_truth() - MUMPS truth evaluation (§1.2.4)."""

    def test_nonzero_integers_are_true(self):
        """Nonzero integers evaluate to True."""
        assert m_truth(1) is True
        assert m_truth(-1) is True
        assert m_truth(42) is True

    def test_zero_is_false(self):
        """Zero evaluates to False."""
        assert m_truth(0) is False
        assert m_truth(0.0) is False
        assert m_truth("0") is False

    def test_empty_string_is_false(self):
        """Empty string evaluates to False (m_num("") = 0)."""
        assert m_truth("") is False

    def test_numeric_strings_evaluated_as_numbers(self):
        """Numeric strings are evaluated via m_num."""
        assert m_truth("1") is True
        assert m_truth("-1") is True
        assert m_truth("0") is False
        assert m_truth("0.0") is False

    def test_strings_with_numeric_prefix(self):
        """Strings with numeric prefix use the numeric part."""
        assert m_truth("1A") is True  # m_num("1A") = 1
        assert m_truth("0A") is False  # m_num("0A") = 0

    def test_non_numeric_strings_are_false(self):
        """Non-numeric strings evaluate to False (m_num returns 0)."""
        assert m_truth("A") is False
        assert m_truth("ABC") is False
        assert m_truth("A1") is False  # No numeric prefix


@pytest.mark.codegen
class TestMCompare:
    """Tests for m_compare() - MUMPS comparison with coercion."""

    # Tests for "=" operator (canonical string equality)

    def test_equal_identical_integers(self):
        """Identical integers are equal."""
        assert m_compare(3, "=", 3) is True
        assert m_compare(0, "=", 0) is True
        assert m_compare(-5, "=", -5) is True

    def test_equal_integer_and_float(self):
        """Integer and equivalent float are equal (both normalize)."""
        assert m_compare(3, "=", 3.0) is True
        assert m_compare(3.0, "=", 3) is True
        assert m_compare(0, "=", 0.0) is True

    def test_equal_string_and_integer(self):
        """String and integer compare by canonical form."""
        assert m_compare("3", "=", 3) is True
        assert m_compare(3, "=", "3") is True
        assert m_compare("0", "=", 0) is True

    def test_equal_string_float_not_equal_to_integer(self):
        """String "3.0" is not equal to canonical "3"."""
        assert m_compare("3.0", "=", 3) is False
        assert m_compare(3, "=", "3.0") is False

    def test_equal_identical_strings(self):
        """Identical string values are equal."""
        assert m_compare("hello", "=", "hello") is True
        assert m_compare("", "=", "") is True

    def test_equal_different_strings(self):
        """Different strings are not equal."""
        assert m_compare("hello", "=", "world") is False
        assert m_compare("3", "=", "4") is False

    # Tests for "<" operator (numeric comparison)

    def test_less_than_numeric(self):
        """Numeric less-than comparison."""
        assert m_compare(1, "<", 2) is True
        assert m_compare(2, "<", 1) is False
        assert m_compare(1, "<", 1) is False

    def test_less_than_with_string_coercion(self):
        """Strings are coerced to numbers for less-than."""
        assert m_compare("3A", "<", 5) is True  # 3 < 5
        assert m_compare("5", "<", "3A") is False  # 5 < 3 is False

    def test_less_than_empty_string_is_zero(self):
        """Empty string coerces to 0 for comparison."""
        assert m_compare("", "<", 1) is True  # 0 < 1
        assert m_compare(1, "<", "") is False  # 1 < 0 is False

    def test_less_than_negative_numbers(self):
        """Negative numbers compare correctly."""
        assert m_compare(-5, "<", -1) is True
        assert m_compare(-1, "<", -5) is False
        assert m_compare(-1, "<", 0) is True

    # Tests for ">" operator (numeric comparison)

    def test_greater_than_numeric(self):
        """Numeric greater-than comparison."""
        assert m_compare(2, ">", 1) is True
        assert m_compare(1, ">", 2) is False
        assert m_compare(1, ">", 1) is False

    def test_greater_than_with_string_coercion(self):
        """Strings are coerced to numbers for greater-than."""
        assert m_compare(5, ">", "3A") is True  # 5 > 3
        assert m_compare("3A", ">", 5) is False  # 3 > 5 is False

    def test_greater_than_negative_numbers(self):
        """Negative numbers compare correctly."""
        assert m_compare(-1, ">", -5) is True
        assert m_compare(-5, ">", -1) is False
        assert m_compare(0, ">", -1) is True

    # Edge cases and error handling

    def test_unsupported_operator_raises_error(self):
        """Unsupported operators raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported comparison operator"):
            m_compare(1, "!=", 2)
        with pytest.raises(ValueError, match="Unsupported comparison operator"):
            m_compare(1, "<=", 2)
