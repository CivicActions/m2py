"""Tests for code generation helper functions.

Tests the helper functions used by generated code to implement MUMPS semantics.

Reference: ANSI MUMPS 7.1.4.5 (numeric coercion), 1.2.4 (truth values)
"""

from decimal import Decimal

import pytest

from m2py.codegen.helpers import (
    m_add,
    m_compare,
    m_div,
    m_mul,
    m_num,
    m_str,
    m_sub,
    m_truth,
)


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
        """Numeric strings with decimals convert to Decimal or int."""
        assert m_num("3.14") == Decimal("3.14")
        assert m_num("3.0") == 3  # Normalized to int
        assert m_num("0.5") == Decimal("0.5")
        assert isinstance(m_num("3.14"), Decimal)
        assert isinstance(m_num("3.0"), int)

    def test_leading_zeros_stripped(self):
        """Leading zeros are stripped per MUMPS canonical form."""
        assert m_num("007") == 7
        assert m_num("0042") == 42
        assert m_num("00.5") == Decimal("0.5")

    def test_leading_whitespace_returns_zero(self):
        """Leading whitespace makes string non-numeric (returns 0).

        NOTE: MUMPS does NOT strip leading whitespace! A space or tab is a
        non-numeric character that stops left-to-right parsing immediately.
        """
        assert m_num("  42") == 0  # Space is not numeric
        assert m_num("\t5") == 0  # Tab is not numeric
        assert m_num("   -3") == 0  # Spaces before sign are not numeric

    def test_trailing_non_numeric_ignored(self):
        """Trailing non-numeric characters are ignored."""
        assert m_num("3A") == 3
        assert m_num("42XYZ") == 42
        assert m_num("3.14ABC") == Decimal("3.14")

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
    """Tests for m_compare() - MUMPS comparison with coercion.

    NOTE: m_compare returns int (0 or 1) per MUMPS semantics, not Python bool.
    """

    # Tests for "=" operator (canonical string equality)

    def test_equal_identical_integers(self):
        """Identical integers are equal."""
        assert m_compare(3, "=", 3) == 1
        assert m_compare(0, "=", 0) == 1
        assert m_compare(-5, "=", -5) == 1

    def test_equal_integer_and_float(self):
        """Integer and equivalent float are equal (both normalize)."""
        assert m_compare(3, "=", 3.0) == 1
        assert m_compare(3.0, "=", 3) == 1
        assert m_compare(0, "=", 0.0) == 1

    def test_equal_string_and_integer(self):
        """String and integer compare by canonical form."""
        assert m_compare("3", "=", 3) == 1
        assert m_compare(3, "=", "3") == 1
        assert m_compare("0", "=", 0) == 1

    def test_equal_string_float_not_equal_to_integer(self):
        """String "3.0" is not equal to canonical "3"."""
        assert m_compare("3.0", "=", 3) == 0
        assert m_compare(3, "=", "3.0") == 0

    def test_equal_identical_strings(self):
        """Identical string values are equal."""
        assert m_compare("hello", "=", "hello") == 1
        assert m_compare("", "=", "") == 1

    def test_equal_different_strings(self):
        """Different strings are not equal."""
        assert m_compare("hello", "=", "world") == 0
        assert m_compare("3", "=", "4") == 0

    # Tests for "<" operator (numeric comparison)

    def test_less_than_numeric(self):
        """Numeric less-than comparison."""
        assert m_compare(1, "<", 2) == 1
        assert m_compare(2, "<", 1) == 0
        assert m_compare(1, "<", 1) == 0

    def test_less_than_with_string_coercion(self):
        """Strings are coerced to numbers for less-than."""
        assert m_compare("3A", "<", 5) == 1  # 3 < 5
        assert m_compare("5", "<", "3A") == 0  # 5 < 3 is False

    def test_less_than_empty_string_is_zero(self):
        """Empty string coerces to 0 for comparison."""
        assert m_compare("", "<", 1) == 1  # 0 < 1
        assert m_compare(1, "<", "") == 0  # 1 < 0 is False

    def test_less_than_negative_numbers(self):
        """Negative numbers compare correctly."""
        assert m_compare(-5, "<", -1) == 1
        assert m_compare(-1, "<", -5) == 0
        assert m_compare(-1, "<", 0) == 1

    # Tests for ">" operator (numeric comparison)

    def test_greater_than_numeric(self):
        """Numeric greater-than comparison."""
        assert m_compare(2, ">", 1) == 1
        assert m_compare(1, ">", 2) == 0
        assert m_compare(1, ">", 1) == 0

    def test_greater_than_with_string_coercion(self):
        """Strings are coerced to numbers for greater-than."""
        assert m_compare(5, ">", "3A") == 1  # 5 > 3
        assert m_compare("3A", ">", 5) == 0  # 3 > 5 is False

    def test_greater_than_negative_numbers(self):
        """Negative numbers compare correctly."""
        assert m_compare(-1, ">", -5) == 1
        assert m_compare(-5, ">", -1) == 0
        assert m_compare(0, ">", -1) == 1

    # Edge cases and error handling

    def test_unsupported_operator_raises_error(self):
        """Unsupported operators raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported comparison operator"):
            m_compare(1, "!=", 2)
        with pytest.raises(ValueError, match="Unsupported comparison operator"):
            m_compare(1, "<=", 2)


@pytest.mark.codegen
class TestMStr:
    """Tests for m_str() - MUMPS string conversion (no scientific notation).

    Spec 017: Bug fix from commit 768a80e1 - Python uses scientific notation
    for very large/small numbers (7e-15, 1e15) but MUMPS never does.
    m_str() ensures consistent MUMPS-style decimal output.
    """

    def test_integer_passthrough(self):
        """Integers convert to simple string."""
        assert m_str(0) == "0"
        assert m_str(1) == "1"
        assert m_str(-5) == "-5"
        assert m_str(42) == "42"

    def test_float_no_scientific_notation(self):
        """Floats that Python would format as scientific stay decimal."""
        # Python str() would give '7e-15' but MUMPS needs decimal
        result = m_str(7e-15)
        assert "e" not in result.lower()
        assert result == ".000000000000007"

        # Large number: Python str() gives '1e+15' but MUMPS needs full form
        result = m_str(1e15)
        assert "e" not in result.lower()
        assert result == "1000000000000000"

    def test_regular_float_preserved(self):
        """Regular floats without scientific notation preserved."""
        assert m_str(3.14) == "3.14"
        assert m_str(-2.5) == "-2.5"
        assert m_str(0.5) == ".5"  # MUMPS canonical: no leading zero

    def test_zero_float(self):
        """Float zero converts to simple '0'."""
        assert m_str(0.0) == "0"

    def test_decimal_type(self):
        """Decimal type for precise large numbers."""
        # Very large number that exceeds float64 precision
        d = Decimal("9999997799E14")
        result = m_str(d)
        assert "e" not in result.lower()
        assert "E" not in result
        assert result == "999999779900000000000000"

    def test_string_passthrough(self):
        """Non-numeric values pass through str()."""
        assert m_str("hello") == "hello"
        assert m_str("") == ""


@pytest.mark.codegen
class TestMNumExponential:
    """Tests for m_num() exponential notation handling.

    Spec 017: Bug fix from commit 768a80e1 - m_num must recognize
    scientific notation in strings like '1E2' → 100.
    """

    def test_exponential_notation_uppercase(self):
        """Uppercase E exponential notation."""
        assert m_num("1E2") == 100
        assert m_num("1E3") == 1000
        assert m_num("5E1") == 50

    def test_exponential_notation_lowercase(self):
        """Lowercase e exponential notation."""
        assert m_num("1e2") == 100
        assert m_num("2.5e2") == 250

    def test_exponential_negative_exponent(self):
        """Negative exponents - returns Decimal to preserve precision."""
        assert m_num("1E-2") == Decimal("0.01")
        assert m_num("5e-1") == Decimal("0.5")

    def test_exponential_positive_exponent_explicit(self):
        """Explicit positive exponent sign."""
        assert m_num("1E+2") == 100
        assert m_num("1e+3") == 1000

    def test_exponential_with_decimal_base(self):
        """Decimal number as base with exponent."""
        assert m_num("1.5E2") == 150
        assert m_num("2.5E-1") == Decimal("0.25")

    def test_exponential_trailing_non_numeric(self):
        """Exponential notation with trailing non-numeric."""
        # After the exponent value, parsing stops
        result = m_num("1E2A")
        # 1E2 = 100, 'A' is ignored
        assert result == 100


# =============================================================================
# Arithmetic Helper Function Tests - m_add, m_sub, m_mul, m_div
# =============================================================================


@pytest.mark.codegen
class TestMAdd:
    """Tests for m_add() - MUMPS addition with 18-digit precision.

    All test cases verified against YDB output.
    """

    # Basic integer addition
    def test_basic_integer_addition(self):
        """Integer addition returns integer.

        YDB: W 2+3 → 5
        """
        assert m_add(2, 3) == 5
        assert isinstance(m_add(2, 3), int)

    def test_zero_addition(self):
        """Adding zero returns the other operand.

        YDB: W 0+5 → 5
        """
        assert m_add(0, 5) == 5
        assert m_add(5, 0) == 5
        assert m_add(0, 0) == 0

    def test_negative_addition(self):
        """Addition with negative numbers.

        YDB: W -5+-3 → -8
        """
        assert m_add(-5, -3) == -8
        assert m_add(-5, 3) == -2
        assert m_add(5, -3) == 2

    # Decimal addition (precision tests)
    def test_decimal_addition_basic(self):
        """Decimal addition preserves precision.

        YDB: W 0.001+0.001 → .002
        """
        result = m_add(0.001, 0.001)
        assert result == Decimal("0.002")

    def test_decimal_addition_no_float_error(self):
        """Avoids classic 0.1+0.2 != 0.3 float error.

        YDB: W 0.1+0.2 → .3
        NOTE: Python float gives 0.30000000000000004
        """
        result = m_add(0.1, 0.2)
        assert result == Decimal("0.3")

    def test_decimal_repeated_addition(self):
        """Repeated small additions don't accumulate float errors.

        YDB: W .1+.1+.1+.1+.1+.1+.1+.1+.1+.1 → 1
        """
        # Simulate repeated addition
        result = Decimal("0.1")
        for _ in range(9):
            result = m_add(result, Decimal("0.1"))
        assert result == 1
        assert isinstance(result, int)

    # String coercion (m_num)
    def test_string_coercion_numeric_prefix(self):
        """Strings with numeric prefix are coerced.

        YDB: W "3A"+4 → 7
        """
        assert m_add("3A", 4) == 7
        assert m_add(4, "3A") == 7

    def test_string_coercion_empty_string(self):
        """Empty string coerces to 0.

        YDB: W ""+5 → 5
        """
        assert m_add("", 5) == 5
        assert m_add(5, "") == 5

    def test_string_coercion_non_numeric(self):
        """Non-numeric strings coerce to 0.

        YDB: W "ABC"+5 → 5
        """
        assert m_add("ABC", 5) == 5
        assert m_add("XYZ", "ABC") == 0

    # Integer normalization
    def test_whole_number_result_normalized(self):
        """Whole number results normalize to int.

        YDB: W 1.5+1.5 → 3
        """
        result = m_add(1.5, 1.5)
        assert result == 3
        assert isinstance(result, int)


@pytest.mark.codegen
class TestMSub:
    """Tests for m_sub() - MUMPS subtraction with 18-digit precision.

    All test cases verified against YDB output.
    """

    # Basic integer subtraction
    def test_basic_integer_subtraction(self):
        """Integer subtraction returns integer.

        YDB: W 5-3 → 2
        """
        assert m_sub(5, 3) == 2
        assert isinstance(m_sub(5, 3), int)

    def test_zero_subtraction(self):
        """Subtracting zero returns operand.

        YDB: W 5-0 → 5
        """
        assert m_sub(5, 0) == 5
        assert m_sub(0, 5) == -5
        assert m_sub(0, 0) == 0

    def test_negative_subtraction(self):
        """Subtraction resulting in negative.

        YDB: W 3-5 → -2
        """
        assert m_sub(3, 5) == -2

    def test_double_negative_subtraction(self):
        """Subtracting negative (addition).

        YDB: W 5-(-3) → 8
        """
        assert m_sub(5, -3) == 8
        assert m_sub(-2, -3) == 1

    # Decimal subtraction
    def test_decimal_subtraction_basic(self):
        """Decimal subtraction preserves precision.

        YDB: W 0.003-0.001 → .002
        """
        result = m_sub(0.003, 0.001)
        assert result == Decimal("0.002")

    def test_decimal_subtraction_no_float_error(self):
        """Avoids float precision errors.

        YDB: W 0.3-0.1 → .2
        NOTE: Python float can have small errors here
        """
        result = m_sub(0.3, 0.1)
        assert result == Decimal("0.2")

    # String coercion
    def test_string_coercion(self):
        """Strings coerced via m_num.

        YDB: W "10X"-3 → 7
        """
        assert m_sub("10X", 3) == 7
        assert m_sub("10", "3A") == 7

    # Integer normalization
    def test_whole_number_result_normalized(self):
        """Whole number results normalize to int.

        YDB: W 5.5-2.5 → 3
        """
        result = m_sub(5.5, 2.5)
        assert result == 3
        assert isinstance(result, int)


@pytest.mark.codegen
class TestMMul:
    """Tests for m_mul() - MUMPS multiplication with 18-digit precision.

    All test cases verified against YDB output.
    """

    # Basic integer multiplication
    def test_basic_integer_multiplication(self):
        """Integer multiplication returns integer.

        YDB: W 3*4 → 12
        """
        assert m_mul(3, 4) == 12
        assert isinstance(m_mul(3, 4), int)

    def test_zero_multiplication(self):
        """Multiplying by zero returns 0.

        YDB: W 5*0 → 0
        """
        assert m_mul(5, 0) == 0
        assert m_mul(0, 5) == 0
        assert m_mul(0, 0) == 0

    def test_one_multiplication(self):
        """Multiplying by 1 returns operand.

        YDB: W 5*1 → 5
        """
        assert m_mul(5, 1) == 5
        assert m_mul(1, 5) == 5

    def test_negative_multiplication(self):
        """Negative number multiplication.

        YDB: W -2*3 → -6
        YDB: W -2*-3 → 6
        """
        assert m_mul(-2, 3) == -6
        assert m_mul(-2, -3) == 6
        assert m_mul(2, -3) == -6

    # Decimal multiplication
    def test_decimal_multiplication_basic(self):
        """Decimal multiplication preserves precision.

        YDB: W 0.01*0.02 → .0002
        """
        result = m_mul(0.01, 0.02)
        assert result == Decimal("0.0002")

    def test_decimal_multiplication_squares(self):
        """Squaring decimals.

        YDB: W 0.1*0.1 → .01
        """
        result = m_mul(0.1, 0.1)
        assert result == Decimal("0.01")

    def test_large_number_multiplication(self):
        """Large number multiplication.

        YDB: W 1E10*1E8 → 1000000000000000000
        """
        result = m_mul(1e10, 1e8)
        assert result == 1000000000000000000

    # String coercion
    def test_string_coercion(self):
        """Strings coerced via m_num.

        YDB: W "5A"*"3B" → 15
        """
        assert m_mul("5A", "3B") == 15
        assert m_mul("5", 3) == 15

    # Integer normalization
    def test_whole_number_result_normalized(self):
        """Whole number results normalize to int.

        YDB: W 2.5*4 → 10
        """
        result = m_mul(2.5, 4)
        assert result == 10
        assert isinstance(result, int)


@pytest.mark.codegen
class TestMDiv:
    """Tests for m_div() - MUMPS division with 18-digit precision.

    All test cases verified against YDB output.
    MUMPS uses 18 significant digits for division precision.
    """

    # Basic division
    def test_basic_even_division(self):
        """Even division returns exact result.

        YDB: W 10/2 → 5
        """
        result = m_div(10, 2)
        assert result == Decimal("5")

    def test_basic_division_with_remainder(self):
        """Division with remainder produces decimal.

        YDB: W 10/4 → 2.5
        """
        result = m_div(10, 4)
        assert result == Decimal("2.5")

    def test_zero_dividend(self):
        """Zero divided by anything is 0.

        YDB: W 0/5 → 0
        """
        result = m_div(0, 5)
        assert result == Decimal("0")

    def test_negative_division(self):
        """Division with negative numbers.

        YDB: W -6/2 → -3
        """
        result = m_div(-6, 2)
        assert result == Decimal("-3")

    # 18-digit precision tests
    def test_repeating_decimal_precision(self):
        """Repeating decimals show 18-digit precision.

        YDB: W 4/3 → 1.33333333333333333
        YDB: W 1/3 → .333333333333333333
        """
        result = m_div(4, 3)
        assert str(result) == "1.33333333333333333"

        result = m_div(1, 3)
        assert str(result) == "0.333333333333333333"

    def test_simple_fraction(self):
        """Simple fractions.

        YDB: W 1/10 → .1
        """
        result = m_div(1, 10)
        assert result == Decimal("0.1")

    # String coercion
    def test_string_coercion(self):
        """Strings coerced via m_num.

        YDB: W "15X"/"3Y" → 5
        """
        result = m_div("15X", "3Y")
        assert result == Decimal("5")

    def test_divide_by_zero_raises(self):
        """Division by zero raises error.

        YDB: W 1/0 → %YDB-E-DIVZERO
        """
        with pytest.raises(ZeroDivisionError):
            m_div(1, 0)


@pytest.mark.codegen
class TestArithmeticMStrFormatting:
    """Tests for m_str() formatting of arithmetic results.

    Ensures arithmetic results format correctly without scientific notation.
    """

    def test_small_decimal_formatting(self):
        """Small decimals don't use scientific notation.

        YDB: S X=0.0002 W X → .0002
        """
        result = m_mul(0.01, 0.02)
        assert m_str(result) == ".0002"

    def test_large_number_formatting(self):
        """Large numbers don't use scientific notation.

        YDB: S X=1000000000000000000 W X → 1000000000000000000
        """
        result = m_mul(1e10, 1e8)
        assert m_str(result) == "1000000000000000000"

    def test_repeating_decimal_formatting(self):
        """Repeating decimals format correctly.

        YDB: S X=1/3 W X → .333333333333333333
        """
        result = m_div(1, 3)
        formatted = m_str(result)
        # Should start with 0. (or just .) and have 18 3's
        assert "e" not in formatted.lower()
        assert formatted == ".333333333333333333"

    def test_very_small_number_formatting(self):
        """Very small numbers format without scientific notation.

        YDB: W 7E-15 → .000000000000007
        """
        assert m_str(7e-15) == ".000000000000007"
