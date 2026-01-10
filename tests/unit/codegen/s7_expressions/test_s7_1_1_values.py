"""Tests for Values code generation (§7.1.1).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.1
"""

import pytest


@pytest.mark.codegen
class TestValuesCodegen:
    """Codegen-level tests for values code generation (§7.1.1)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: string value")
    def test_string_value(self, generate_python):
        """String values generate Python strings (§7.1.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: numeric value")
    def test_numeric_value(self, generate_python):
        """Numeric values generate Python numbers (§7.1.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: empty string")
    def test_empty_string(self, generate_python):
        """Empty string generates empty Python string (§7.1.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: MValue wrapper")
    def test_mvalue_wrapper(self, generate_python):
        """Values use MValue wrapper for MUMPS semantics (§7.1.1)."""
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestNumericCoercionCodegen:
    """Codegen tests for MUMPS numeric coercion helper (m_num).

    MUMPS coerces strings to numbers by scanning left-to-right for the
    longest valid numeric prefix. This is critical for all arithmetic
    and comparison operations.

    Reference: §7.1.4.5
    """

    def test_empty_string_returns_zero(self):
        """Empty string coerces to 0.

        User Story 6 acceptance scenario (T049):
        m_num("") returns 0 per MUMPS semantics.
        """
        from m2py.codegen.helpers import m_num

        assert m_num("") == 0

    def test_leading_zeros_canonicalized(self):
        """Leading zeros are stripped (canonicalized) during numeric coercion.

        User Story 6 acceptance scenario (T050):
        m_num("007") returns 7 (not 7 as octal, just strip leading zeros).
        """
        from m2py.codegen.helpers import m_num

        assert m_num("007") == 7

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: numeric prefix extraction")
    def test_numeric_prefix_extraction(self, generate_python):
        """Numeric coercion extracts leading numeric prefix.

        '3A' coerces to 3, 'A3' coerces to 0 (no leading numeric).
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: empty string to zero")
    def test_empty_string_to_zero(self, generate_python):
        """Empty string coerces to 0.

        '' coerces to 0 per MUMPS semantics.
        """
        pytest.fail("Stub - implement test")

    def test_sign_canonicalization(self):
        """Numeric coercion canonicalizes signs.

        Phase 10 validation: Test sign handling edge cases.
        '  +42' coerces to 42, '--5' coerces to 5, '+-5' coerces to -5.
        """
        from m2py.codegen.helpers import m_num

        # Positive sign
        assert m_num("+42") == 42
        # Double negative
        assert m_num("--5") == 5
        # Mixed signs
        assert m_num("+-5") == -5
        assert m_num("-+5") == -5
        # Leading whitespace with sign
        assert m_num("  +42") == 42
        # Just signs (no digits)
        assert m_num("++") == 0
        assert m_num("-") == 0

    def test_decimal_handling(self):
        """Numeric coercion handles decimals correctly.

        Phase 10 validation: Test decimal number parsing.
        '3.14ABC' coerces to 3.14, '.5' coerces to 0.5.
        """
        from m2py.codegen.helpers import m_num

        # Decimal with trailing text
        assert m_num("3.14ABC") == 3.14
        # Leading decimal
        assert m_num(".5") == 0.5
        # Integer that looks like float
        assert m_num("3.0") == 3  # Returns int when possible
        # Lone decimal point
        assert m_num(".") == 0
        # Already numeric (float pass-through)
        assert m_num(3.14) == 3.14
        # Already numeric (int pass-through)
        assert m_num(42) == 42


@pytest.mark.codegen
class TestTruthValueCodegen:
    """Codegen tests for MUMPS truth value helper (m_truth).

    Truth in MUMPS is numeric-based: 0 is false, all nonzero is true.
    This affects IF conditions, postconditions, and logical operators.

    Reference: §1.2.4
    """

    def test_zero_is_false(self):
        """Numeric 0 evaluates to false.

        Phase 10 validation: '0', '', 'A' all coerce to 0 → false.
        """
        from m2py.codegen.helpers import m_truth

        assert m_truth(0) is False
        assert m_truth("0") is False
        assert m_truth("") is False
        assert m_truth("A") is False

    def test_nonzero_is_true(self):
        """Any nonzero numeric evaluates to true.

        Phase 10 validation: '1', '3.14', '1A', '-5' all coerce to nonzero → true.
        """
        from m2py.codegen.helpers import m_truth

        assert m_truth(1) is True
        assert m_truth("1") is True
        assert m_truth("3.14") is True
        assert m_truth("1A") is True
        assert m_truth("-5") is True

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: string with leading number")
    def test_string_with_leading_number(self, generate_python):
        """String with leading number uses numeric truth.

        '1ABC' is true (coerces to 1), '0ABC' is false (coerces to 0).
        """
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestComparisonCodegen:
    """Codegen tests for MUMPS comparison helper (m_compare).

    MUMPS comparison operators (<, >) force numeric evaluation on both
    operands before comparing. Equality (=) compares string values.

    Reference: §7.2
    """

    def test_numeric_comparison(self):
        """Less-than/greater-than use numeric coercion.

        Phase 10 validation: '3' < '10' is true (3 < 10), 'A' < 'B' compares 0 < 0.
        """
        from m2py.codegen.helpers import m_compare

        assert m_compare("3", "<", "10") is True
        assert m_compare("3", ">", "10") is False
        assert m_compare("A", "<", "B") is False  # 0 < 0 is false
        assert m_compare("3A", "<", 5) is True  # 3 < 5

    def test_string_equality(self):
        """Equality compares string values directly.

        Phase 10 validation: '3' = '03' is false (string comparison).
        """
        from m2py.codegen.helpers import m_compare

        assert m_compare("3", "=", "3") is True
        assert m_compare("3", "=", "03") is False  # String comparison
        assert m_compare(3, "=", 3) is True

    def test_invalid_operator_raises(self):
        """Invalid comparison operator raises ValueError.

        Phase 10 validation: Cover error path.
        """
        import pytest
        from m2py.codegen.helpers import m_compare

        with pytest.raises(ValueError, match="Unsupported comparison operator"):
            m_compare(1, "!=", 2)
