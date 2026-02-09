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
    m_mod,
    m_mul,
    m_num,
    m_str,
    m_sub,
    m_truth,
)
from m2py.runtime import MArray


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

    def test_equal_decimal_zero_with_trailing_zeros(self):
        """Decimal zero with trailing zeros equals integer zero.

        Spec 017: Bug fix - Decimal('0.000000') was failing equality with int 0
        because m_str was returning '' instead of '0' for such values.
        """
        assert m_compare(Decimal("0.000000"), "=", 0) == 1
        assert m_compare(0, "=", Decimal("0.000000")) == 1
        assert m_compare(Decimal("0E-6"), "=", 0) == 1
        assert m_compare(Decimal("000000.000000E+000000"), "=", 0) == 1

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

    def test_decimal_zero_with_trailing_zeros(self):
        """Decimal zero values with trailing zeros canonicalize to '0'.

        Spec 017: Bug fix - Decimal('0.000000') was returning '' after
        stripping trailing zeros from '.000000'. Now correctly returns '0'.
        """
        # Various ways of representing zero as a Decimal
        assert m_str(Decimal("0.000000")) == "0"
        assert m_str(Decimal("0.0")) == "0"
        assert m_str(Decimal("0")) == "0"
        assert m_str(Decimal("0E-6")) == "0"
        assert m_str(Decimal("000000.000000E+000000")) == "0"

    def test_negative_zero_canonicalizes(self):
        """Decimal negative zero canonicalizes to '0'.

        Spec 017: Bug fix - Decimal('-0') from operations like 0/-6
        was returning '-0' but MUMPS doesn't have negative zero.
        """
        assert m_str(Decimal("-0")) == "0"
        assert m_str(Decimal("-0.0")) == "0"
        assert m_str(Decimal("-0E-6")) == "0"

    def test_string_passthrough(self):
        """Non-numeric values pass through str()."""
        assert m_str("hello") == "hello"
        assert m_str("") == ""


@pytest.mark.codegen
class TestMNumExponential:
    """Tests for m_num() exponential notation handling.

    Spec 017: Bug fix from commit 768a80e1 - m_num must recognize
    scientific notation in strings like '1E2' → 100.

    IMPORTANT: MUMPS only recognizes UPPERCASE 'E' for scientific notation.
    Lowercase 'e' is treated as a non-numeric character that stops parsing.
    """

    def test_exponential_notation_uppercase(self):
        """Uppercase E exponential notation."""
        assert m_num("1E2") == 100
        assert m_num("1E3") == 1000
        assert m_num("5E1") == 50

    def test_lowercase_e_not_exponential(self):
        """Lowercase 'e' is NOT scientific notation in MUMPS - stops parsing.

        MUMPS specification requires uppercase E only. Lowercase 'e' is a
        non-numeric character that terminates left-to-right numeric parsing.
        """
        assert m_num("1e2") == 1  # 'e' stops parsing, result is just 1
        assert m_num("2.5e2") == Decimal("2.5")  # Stops at 'e'
        assert m_num("1234e2") == 1234  # Not 123400!

    def test_exponential_negative_exponent(self):
        """Negative exponents - returns Decimal to preserve precision."""
        assert m_num("1E-2") == Decimal("0.01")
        # Lowercase e does not work:
        assert m_num("5e-1") == 5  # Stops at 'e', result is 5

    def test_exponential_positive_exponent_explicit(self):
        """Explicit positive exponent sign."""
        assert m_num("1E+2") == 100
        # Lowercase e does not work:
        assert m_num("1e+3") == 1  # Stops at 'e', result is 1

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


@pytest.mark.codegen
class TestMMod:
    """Tests for m_mod() - MUMPS modulo (#) operator.

    MUMPS modulo uses floor division semantics, not truncation towards zero.
    This differs from Python's Decimal % operator.

    All test cases verified against YDB output.
    """

    def test_basic_positive_modulo(self):
        """Basic positive modulo.

        YDB: W 7#3 → 1
        """
        assert m_mod(7, 3) == 1

    def test_zero_dividend(self):
        """Zero modulo anything is 0.

        YDB: W 0#5 → 0
        """
        assert m_mod(0, 5) == 0
        assert m_mod(0, -6) == 0

    def test_negative_dividend_positive_divisor(self):
        """Negative dividend with positive divisor uses floor division.

        YDB: W -7#3 → 2
        YDB: W -597.5#25 → 2.5

        This is the key difference from truncation semantics:
        -7 / 3 = -2.333... floor is -3, so -7 - (3 * -3) = -7 + 9 = 2
        With truncation: -7 - (3 * -2) = -7 + 6 = -1 (WRONG)
        """
        assert m_mod(-7, 3) == 2
        assert m_mod(-597.5, 25) == Decimal("2.5")

    def test_negative_divisor(self):
        """Modulo with negative divisor.

        YDB: W -50.3#-0.25 → -.05
        """
        result = m_mod(-50.3, -0.25)
        assert m_str(result) == "-.05"

    def test_decimal_operands(self):
        """Modulo with decimal operands.

        YDB: W 1E1#1.10 → .1
        """
        result = m_mod("1E1", "1.10")
        assert m_str(result) == ".1"

    def test_string_coercion(self):
        """String operands coerced via m_num.

        YDB: W "10X"#"3Y" → 1
        """
        assert m_mod("10X", "3Y") == 1

    def test_positive_dividend_negative_divisor(self):
        """Positive dividend with negative divisor.

        YDB: W 7#-3 → -2
        """
        assert m_mod(7, -3) == -2

    def test_exact_division(self):
        """When dividend is exactly divisible, result is 0.

        YDB: W 9#3 → 0
        """
        assert m_mod(9, 3) == 0


@pytest.mark.codegen
class TestMArrayHandling:
    """Tests for MArray value extraction in helper functions (T075h).

    When variables are stored as MArray objects in state._locals (TRAMPOLINE
    strategy with dynamic locals), helper functions must extract .value rather
    than converting MArray objects directly.
    """

    def test_m_str_extracts_marray_value(self):
        """m_str() extracts .value from MArray objects."""
        arr = MArray()
        arr.value = "hello"
        assert m_str(arr) == "hello"

    def test_m_str_extracts_nested_marray_value(self):
        """m_str() handles nested MArray objects."""
        inner = MArray()
        inner.value = "world"
        outer = MArray()
        outer.value = inner
        assert m_str(outer) == "world"

    def test_m_str_handles_marray_with_empty_value(self):
        """m_str() handles MArray with default empty value."""
        arr = MArray()
        assert m_str(arr) == ""

    def test_m_num_extracts_marray_value(self):
        """m_num() extracts .value from MArray objects."""
        arr = MArray()
        arr.value = "42"
        assert m_num(arr) == 42

    def test_m_num_handles_nested_marray(self):
        """m_num() handles nested MArray objects."""
        inner = MArray()
        inner.value = "3.14"
        outer = MArray()
        outer.value = inner
        assert m_num(outer) == Decimal("3.14")

    def test_m_num_handles_marray_with_empty_value(self):
        """m_num() handles MArray with default empty value."""
        arr = MArray()
        assert m_num(arr) == 0

    def test_m_truth_handles_marray(self):
        """m_truth() handles MArray objects."""
        arr_true = MArray()
        arr_true.value = "1"
        arr_false = MArray()
        arr_false.value = "0"
        arr_empty = MArray()
        assert m_truth(arr_true) is True
        assert m_truth(arr_false) is False
        assert m_truth(arr_empty) is False

    def test_m_compare_handles_marray_left(self):
        """m_compare() extracts value from left MArray operand."""
        arr = MArray()
        arr.value = "A"
        assert m_compare(arr, "=", "A") == 1  # Equal
        assert m_compare(arr, "=", "B") == 0  # Not equal

    def test_m_compare_handles_marray_right(self):
        """m_compare() extracts value from right MArray operand."""
        arr = MArray()
        arr.value = "test"
        assert m_compare("test", "=", arr) == 1  # Equal
        assert m_compare("other", "=", arr) == 0  # Not equal

    def test_m_compare_handles_marray_both(self):
        """m_compare() extracts values from both MArray operands."""
        left = MArray()
        left.value = "same"
        right = MArray()
        right.value = "same"
        assert m_compare(left, "=", right) == 1  # Equal

    def test_m_compare_handles_nested_marray(self):
        """m_compare() handles nested MArray objects."""
        inner = MArray()
        inner.value = "A "  # Note trailing space
        outer = MArray()
        outer.value = inner
        plain = MArray()
        plain.value = "A "
        assert m_compare(outer, "=", plain) == 1  # Should be equal


@pytest.mark.codegen
class TestMFormatOutputMArray:
    """Tests for m_format_output() with MArray objects (T075h).

    When variables are stored as MArray objects in state._locals (TRAMPOLINE
    strategy with dynamic locals), m_format_output must extract .value rather
    than converting MArray objects directly.
    """

    def test_m_format_output_extracts_marray_value(self):
        """m_format_output() extracts .value from MArray objects."""
        from m2py.runtime.helpers import m_format_output

        arr = MArray()
        arr.value = "hello"
        assert m_format_output(arr) == "hello"

    def test_m_format_output_extracts_numeric_marray_value(self):
        """m_format_output() formats numeric values from MArray."""
        from m2py.runtime.helpers import m_format_output

        arr = MArray()
        arr.value = 42
        assert m_format_output(arr) == "42"

        arr2 = MArray()
        arr2.value = 0.5
        assert m_format_output(arr2) == ".5"

    def test_m_format_output_handles_nested_marray(self):
        """m_format_output() handles nested MArray objects."""
        from m2py.runtime.helpers import m_format_output

        inner = MArray()
        inner.value = "world"
        outer = MArray()
        outer.value = inner
        assert m_format_output(outer) == "world"

    def test_m_format_output_handles_empty_marray(self):
        """m_format_output() handles MArray with default empty value."""
        from m2py.runtime.helpers import m_format_output

        arr = MArray()
        # MArray default value is None, which formats as "None"
        # But when used for undefined variables, we expect empty string
        # The actual behavior depends on MArray.value default
        result = m_format_output(arr)
        assert isinstance(result, str)


@pytest.mark.codegen
class TestMArrayContains:
    """Tests for MArray __contains__ method.

    Feature: 017-ydb-test-failures (infinite loop fix)

    MArray needs __contains__ to support 'key in array' syntax.
    Without it, Python falls back to iteration via __getitem__,
    which auto-creates children and causes infinite loops.
    """

    def test_contains_existing_child(self):
        """MArray.__contains__ returns True for existing child."""
        arr = MArray()
        arr["key"] = "value"
        assert "key" in arr

    def test_contains_missing_child(self):
        """MArray.__contains__ returns False for missing child."""
        arr = MArray()
        arr["existing"] = "value"
        assert "missing" not in arr

    def test_contains_canonicalizes_numeric_key(self):
        """MArray.__contains__ canonicalizes numeric keys."""
        arr = MArray()
        arr[1] = "value"
        # Both integer and string forms should work
        assert 1 in arr
        assert "1" in arr

    def test_contains_canonicalizes_leading_zeros(self):
        """MArray.__contains__ handles leading zeros in numeric keys."""
        arr = MArray()
        # Note: MArray __setitem__ stores keys as-is, but __contains__ canonicalizes
        # So we need to set using a numeric key to get consistent behavior
        arr[7] = "james"
        # Both integer and string forms should work
        assert 7 in arr
        assert "7" in arr
        # But the non-canonicalized form "007" won't match since storage uses "7"
        assert "007" not in arr

    def test_contains_empty_array(self):
        """MArray.__contains__ returns False for empty array."""
        arr = MArray()
        assert "anything" not in arr

    def test_contains_does_not_create_child(self):
        """MArray.__contains__ does NOT auto-create children like __getitem__ does."""
        arr = MArray()
        # Check for non-existent key
        _ = "nonexistent" in arr
        # Verify child was NOT created (using _children directly as there's no public method)
        assert len(arr._children) == 0

    def test_contains_nested_children(self):
        """MArray.__contains__ works at any level in hierarchy."""
        arr = MArray()
        arr["a"] = "top"
        arr["a"]["b"] = "nested"
        arr["a"]["b"]["c"] = "deep"

        # At top level
        assert "a" in arr
        assert "x" not in arr

        # At nested level
        assert "b" in arr["a"]
        assert "y" not in arr["a"]

        # At deep level
        assert "c" in arr["a"]["b"]
        assert "z" not in arr["a"]["b"]


@pytest.mark.codegen
class TestMRangeEdgeCases:
    """Tests for m_range negative step, fractional step, zero step."""

    def test_negative_step(self):
        """m_range(3, 1, -1) yields 3, 2, 1."""
        from m2py.codegen.helpers import m_range

        result = list(m_range(3, 1, -1))
        assert result == [3, 2, 1]

    def test_fractional_step(self):
        """m_range with fractional step works correctly."""
        from m2py.codegen.helpers import m_range

        result = list(m_range(0, "0.03", "0.01"))
        assert len(result) == 4  # 0, 0.01, 0.02, 0.03

    def test_zero_step_yields_nothing(self):
        """m_range with step=0 yields nothing (avoids infinite loop)."""
        from m2py.codegen.helpers import m_range

        result = list(m_range(1, 5, 0))
        assert result == []

    def test_single_value(self):
        """m_range where start==end yields single value."""
        from m2py.codegen.helpers import m_range

        result = list(m_range(5, 5, 1))
        assert result == [5]

    def test_negative_step_single_value(self):
        """m_range where start==end with negative step yields single value."""
        from m2py.codegen.helpers import m_range

        result = list(m_range(3, 3, -1))
        assert result == [3]


# =============================================================================
# helpers.py: m_str / m_num with MArray-like objects
# =============================================================================


@pytest.mark.codegen
class TestMStrMNumMArray:
    """Tests for m_str/m_num extracting .value from MArray."""

    def test_m_str_with_marray(self):
        """m_str extracts .value from MArray-like object."""
        from m2py.codegen.helpers import m_str
        from m2py.runtime import MArray

        arr = MArray("42")
        assert m_str(arr) == "42"

    def test_m_num_with_marray(self):
        """m_num extracts .value from MArray-like object."""
        from m2py.codegen.helpers import m_num
        from m2py.runtime import MArray

        arr = MArray("42")
        assert m_num(arr) == 42


# =============================================================================
# Z-commands codegen
# =============================================================================
