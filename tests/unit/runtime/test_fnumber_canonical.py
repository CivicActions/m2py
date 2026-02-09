"""Unit tests for m_fnumber and is_canonical_numeric_string runtime helpers.

Phase 24: Tests for the rewritten m_fnumber function with composable sign codes,
Decimal precision, and 3-arg formatting. Also tests is_canonical_numeric_string
from SubscriptCanonicalizer.
"""

from decimal import Decimal


from m2py.core.subscripts import SubscriptCanonicalizer
from m2py.runtime.helpers import m_fnumber


# =============================================================================
# m_fnumber tests
# =============================================================================


class TestMFnumberBasic:
    """Basic 2-arg m_fnumber with single codes."""

    def test_comma_positive_integer(self):
        assert m_fnumber(12345, ",") == "12,345"

    def test_comma_negative_integer(self):
        assert m_fnumber(-12345, ",") == "-12,345"

    def test_comma_with_decimals(self):
        assert m_fnumber(12345.67, ",") == "12,345.67"

    def test_comma_small_number(self):
        assert m_fnumber(123, ",") == "123"

    def test_comma_zero(self):
        assert m_fnumber(0, ",") == "0"

    def test_comma_one_thousand(self):
        assert m_fnumber(1000, ",") == "1,000"

    def test_comma_millions(self):
        assert m_fnumber(1234567890, ",") == "1,234,567,890"

    def test_plus_positive(self):
        assert m_fnumber(42, "+") == "+42"

    def test_plus_zero(self):
        """Zero is not positive — no + sign."""
        assert m_fnumber(0, "+") == "0"

    def test_plus_negative(self):
        """Plus code does NOT suppress minus."""
        assert m_fnumber(-42, "+") == "-42"

    def test_minus_negative(self):
        """Minus code suppresses the minus sign."""
        assert m_fnumber(-42, "-") == "42"

    def test_minus_positive(self):
        """Minus code is a no-op for positive values."""
        assert m_fnumber(42, "-") == "42"

    def test_minus_zero(self):
        assert m_fnumber(0, "-") == "0"

    def test_p_negative(self):
        """P wraps negative in parentheses."""
        assert m_fnumber(-42, "P") == "(42)"

    def test_p_positive(self):
        """P adds leading and trailing space for non-negative."""
        assert m_fnumber(42, "P") == " 42 "

    def test_p_zero(self):
        """P adds spaces for zero (zero is non-negative)."""
        assert m_fnumber(0, "P") == " 0 "

    def test_t_positive(self):
        """T trailing: positive gets trailing space."""
        assert m_fnumber(42, "T") == "42 "

    def test_t_negative(self):
        """T trailing: negative gets trailing minus."""
        assert m_fnumber(-42, "T") == "42-"

    def test_t_zero(self):
        """T trailing: zero gets trailing space."""
        assert m_fnumber(0, "T") == "0 "


class TestMFnumberComposedCodes:
    """Composable code combinations."""

    def test_t_minus_negative(self):
        """T- suppresses minus, trailing space."""
        assert m_fnumber(-20, "T-") == "20 "

    def test_t_minus_positive(self):
        """T- positive: trailing space (no effect from -)."""
        assert m_fnumber(20, "T-") == "20 "

    def test_t_plus_positive(self):
        """T+ positive: trailing plus sign."""
        assert m_fnumber(42, "T+") == "42+"

    def test_t_plus_negative(self):
        """T+ negative: trailing minus (+ doesn't suppress -)."""
        assert m_fnumber(-42, "T+") == "42-"

    def test_plus_t_equals_t_plus(self):
        """Code order doesn't matter: +T == T+."""
        assert m_fnumber(42, "+T") == m_fnumber(42, "T+")
        assert m_fnumber(-42, "+T") == m_fnumber(-42, "T+")

    def test_plus_minus_positive(self):
        """+ and - compose: positive gets +."""
        assert m_fnumber(42, "+-") == "+42"

    def test_plus_minus_negative(self):
        """+ and - compose: negative gets no sign (- suppresses)."""
        assert m_fnumber(-42, "+-") == "42"

    def test_comma_plus(self):
        assert m_fnumber(12345, ",+") == "+12,345"

    def test_comma_minus_negative(self):
        assert m_fnumber(-12345, ",-") == "12,345"

    def test_comma_t_negative(self):
        assert m_fnumber(-12345, ",T") == "12,345-"

    def test_t_plus_zero(self):
        """T+ with zero: trailing space (zero is not positive)."""
        assert m_fnumber(0, "T+") == "0 "


class TestMFnumberThreeArg:
    """3-arg form with decimals parameter."""

    def test_zero_decimals_integer(self):
        assert m_fnumber(42, ",", 0) == "42"

    def test_two_decimals(self):
        assert m_fnumber(42, ",", 2) == "42.00"

    def test_two_decimals_negative(self):
        assert m_fnumber(-42.5, ",", 2) == "-42.50"

    def test_four_decimals(self):
        assert m_fnumber(12345.6, ",", 4) == "12,345.6000"

    def test_rounding_half_up(self):
        """Rounds 0.5 up (banker's rounding NOT used)."""
        assert m_fnumber(1.235, "+", 2) == "+1.24"

    def test_rounding_down(self):
        assert m_fnumber(1.234, "+", 2) == "+1.23"

    def test_leading_zero_three_arg(self):
        """3-arg form preserves leading zero: 0.xx not .xx."""
        assert m_fnumber(0.5, ",", 2) == "0.50"

    def test_p_with_decimals(self):
        assert m_fnumber(-42, "P", 2) == "(42.00)"

    def test_t_with_decimals(self):
        assert m_fnumber(-42, "T", 2) == "42.00-"

    def test_comma_with_large_number_and_decimals(self):
        assert m_fnumber(1234567, ",", 2) == "1,234,567.00"

    def test_small_fraction_three_arg(self):
        """Small fractions get leading zero in 3-arg form."""
        assert m_fnumber(0.004596, "+", 4) == "+0.0046"


class TestMFnumberCanonical:
    """2-arg form uses MUMPS canonical formatting."""

    def test_no_leading_zero_two_arg(self):
        """2-arg form: fractions < 1 have no leading zero (.5 not 0.5)."""
        assert m_fnumber(0.5, "+") == "+.5"

    def test_negative_fraction_no_leading_zero(self):
        """2-arg negative fraction: -.5 not -0.5."""
        assert m_fnumber(-0.5, "T") == ".5-"

    def test_trailing_zeros_stripped_two_arg(self):
        """2-arg form strips trailing zeros."""
        result = m_fnumber(1.50, ",")
        assert result == "1.5"


class TestMFnumberDecimalPrecision:
    """Tests for large numbers and Decimal precision edge cases."""

    def test_large_number_with_commas(self):
        """Large numbers don't lose precision."""
        result = m_fnumber(Decimal("12345678901234567890"), ",", 0)
        assert result == "12,345,678,901,234,567,890"

    def test_large_number_with_decimals(self):
        """Large number + decimal places doesn't cause InvalidOperation."""
        result = m_fnumber(Decimal("12345678901234567890"), "+", 4)
        assert result == "+12345678901234567890.0000"

    def test_decimal_input(self):
        """Accepts Decimal input directly."""
        result = m_fnumber(Decimal("42.5"), ",", 2)
        assert result == "42.50"

    def test_float_input(self):
        """Float converted to Decimal via str to avoid precision issues."""
        result = m_fnumber(42.5, ",", 2)
        assert result == "42.50"

    def test_int_input(self):
        result = m_fnumber(42, "+", 0)
        assert result == "+42"


class TestMFnumberCaseInsensitive:
    """Format codes are case-insensitive."""

    def test_lowercase_t(self):
        assert m_fnumber(-42, "t") == "42-"

    def test_lowercase_p(self):
        assert m_fnumber(-42, "p") == "(42)"

    def test_mixed_case(self):
        assert m_fnumber(42, "t+") == "42+"


class TestMFnumberEdgeCases:
    """Edge cases for m_fnumber not covered by basic tests."""

    def test_p_with_comma(self):
        """P+comma: parentheses AND thousands separators."""
        assert m_fnumber(-12345, ",P") == "(12,345)"

    def test_p_with_comma_positive(self):
        """P+comma positive: space-padded with commas."""
        assert m_fnumber(12345, ",P") == " 12,345 "

    def test_p_with_comma_and_decimals(self):
        """P+comma+decimals: full formatting."""
        assert m_fnumber(-12345.678, ",P", 2) == "(12,345.68)"

    def test_negative_decimal_zero(self):
        """Decimal('-0') should format as '0' not '-0'."""
        result = m_fnumber(Decimal("-0"), "+")
        assert result == "0"

    def test_three_arg_zero_with_decimals(self):
        """Zero with decimal places."""
        assert m_fnumber(0, ",", 4) == "0.0000"

    def test_three_arg_integer_rounding_boundary(self):
        """Rounding at integer boundary: 2.5 rounds up to 3."""
        assert m_fnumber(2.5, "+", 0) == "+3"

    def test_three_arg_negative_rounding(self):
        """Negative rounding: -2.5 rounds to -3."""
        assert m_fnumber(-2.5, "", 0) == "-3"

    def test_six_digit_number_comma(self):
        """999999 (6 digits) gets comma: 999,999."""
        assert m_fnumber(999999, ",") == "999,999"

    def test_three_digit_number_no_comma(self):
        """999 (3 digits) gets no comma."""
        assert m_fnumber(999, ",") == "999"

    def test_very_small_fraction_three_arg(self):
        """Very small fraction with high decimal places."""
        assert m_fnumber(Decimal("0.000001"), ",", 6) == "0.000001"

    def test_t_plus_minus_all_three(self):
        """T+- combined: trailing position, + for positive, - suppresses."""
        assert m_fnumber(42, "T+-") == "42+"
        assert m_fnumber(-42, "T+-") == "42 "
        assert m_fnumber(0, "T+-") == "0 "

    def test_decimal_fraction_two_arg_canonical(self):
        """Decimal('.004596') in 2-arg form: canonical, no leading zero."""
        assert m_fnumber(Decimal(".004596"), "+") == "+.004596"

    def test_negative_decimal_fraction_two_arg(self):
        """Negative small fraction in 2-arg form."""
        assert m_fnumber(Decimal("-.004596"), "T") == ".004596-"


# =============================================================================
# SubscriptCanonicalizer.is_canonical_numeric_string tests
# =============================================================================


class TestIsCanonicalNumeric:
    """Tests for SubscriptCanonicalizer.is_canonical_numeric_string using m_str(Decimal) comparison."""

    def test_zero(self):
        assert SubscriptCanonicalizer.is_canonical_numeric_string("0") is True

    def test_positive_integer(self):
        assert SubscriptCanonicalizer.is_canonical_numeric_string("42") is True

    def test_negative_integer(self):
        assert SubscriptCanonicalizer.is_canonical_numeric_string("-42") is True

    def test_positive_decimal(self):
        assert SubscriptCanonicalizer.is_canonical_numeric_string("3.14") is True

    def test_negative_decimal(self):
        assert SubscriptCanonicalizer.is_canonical_numeric_string("-3.14") is True

    def test_fraction_without_leading_zero(self):
        """MUMPS canonical: .5 not 0.5."""
        assert SubscriptCanonicalizer.is_canonical_numeric_string(".5") is True

    def test_negative_fraction_without_leading_zero(self):
        """MUMPS canonical: -.5 not -0.5."""
        assert SubscriptCanonicalizer.is_canonical_numeric_string("-.5") is True

    def test_small_fraction(self):
        """Small fractions like .04596 are canonical."""
        assert SubscriptCanonicalizer.is_canonical_numeric_string(".04596") is True

    def test_negative_small_fraction(self):
        assert SubscriptCanonicalizer.is_canonical_numeric_string("-.04596") is True

    # --- Non-canonical forms ---

    def test_leading_zero_not_canonical(self):
        """0.5 is NOT canonical (should be .5)."""
        assert SubscriptCanonicalizer.is_canonical_numeric_string("0.5") is False

    def test_negative_leading_zero_not_canonical(self):
        assert SubscriptCanonicalizer.is_canonical_numeric_string("-0.5") is False

    def test_trailing_zeros_not_canonical(self):
        """Trailing zeros are not canonical."""
        assert SubscriptCanonicalizer.is_canonical_numeric_string("1.50") is False

    def test_leading_zeros_not_canonical(self):
        assert SubscriptCanonicalizer.is_canonical_numeric_string("042") is False

    def test_plus_sign_not_canonical(self):
        """Explicit plus sign is not canonical."""
        assert SubscriptCanonicalizer.is_canonical_numeric_string("+42") is False

    def test_negative_zero_not_canonical(self):
        assert SubscriptCanonicalizer.is_canonical_numeric_string("-0") is False

    def test_trailing_dot_not_canonical(self):
        assert SubscriptCanonicalizer.is_canonical_numeric_string("42.") is False

    # --- Non-numeric strings ---

    def test_empty_string(self):
        assert SubscriptCanonicalizer.is_canonical_numeric_string("") is False

    def test_alphabetic(self):
        assert SubscriptCanonicalizer.is_canonical_numeric_string("abc") is False

    def test_mixed_alphanumeric(self):
        assert SubscriptCanonicalizer.is_canonical_numeric_string("12abc") is False

    def test_spaces(self):
        assert SubscriptCanonicalizer.is_canonical_numeric_string(" 42 ") is False

    # --- Boundary cases ---

    def test_single_digit(self):
        assert SubscriptCanonicalizer.is_canonical_numeric_string("1") is True

    def test_large_integer(self):
        assert (
            SubscriptCanonicalizer.is_canonical_numeric_string("12345678901234567890")
            is True
        )

    def test_scientific_notation_string(self):
        """Scientific notation like '1E2' is not canonical MUMPS form.
        Canonical would be '100'."""
        assert SubscriptCanonicalizer.is_canonical_numeric_string("1E2") is False

    def test_scientific_notation_negative_exponent(self):
        """'1E-2' is not canonical (should be '.01')."""
        assert SubscriptCanonicalizer.is_canonical_numeric_string("1E-2") is False

    def test_lone_decimal_point(self):
        """A lone decimal point is not a valid number."""
        assert SubscriptCanonicalizer.is_canonical_numeric_string(".") is False

    def test_double_zeros(self):
        """'00' is not canonical (should be '0')."""
        assert SubscriptCanonicalizer.is_canonical_numeric_string("00") is False

    def test_just_minus_sign(self):
        """Just a minus sign is not a number."""
        assert SubscriptCanonicalizer.is_canonical_numeric_string("-") is False

    def test_just_plus_sign(self):
        """Just a plus sign is not a number."""
        assert SubscriptCanonicalizer.is_canonical_numeric_string("+") is False

    def test_negative_zero_decimal(self):
        """'-.0' is not canonical."""
        assert SubscriptCanonicalizer.is_canonical_numeric_string("-.0") is False

    def test_infinity_string(self):
        """'Infinity' is not a canonical MUMPS number."""
        assert SubscriptCanonicalizer.is_canonical_numeric_string("Infinity") is False

    def test_nan_string(self):
        """'NaN' is not a canonical MUMPS number."""
        assert SubscriptCanonicalizer.is_canonical_numeric_string("NaN") is False

    def test_very_long_decimal(self):
        """Long decimals are canonical if properly formatted (no trailing zero)."""
        assert (
            SubscriptCanonicalizer.is_canonical_numeric_string(
                ".12345678901234567890123456789"
            )
            is True
        )

    def test_very_long_decimal_trailing_zero_not_canonical(self):
        """Long decimal with trailing zero is not canonical."""
        assert (
            SubscriptCanonicalizer.is_canonical_numeric_string(
                ".123456789012345678901234567890"
            )
            is False
        )

    def test_negative_very_long_decimal(self):
        assert (
            SubscriptCanonicalizer.is_canonical_numeric_string(
                "-.12345678901234567890123456789"
            )
            is True
        )
