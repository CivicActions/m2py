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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: sign canonicalization")
    def test_sign_canonicalization(self, generate_python):
        """Numeric coercion canonicalizes signs.

        '  +42' coerces to 42, '--5' may need special handling.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: decimal handling")
    def test_decimal_handling(self, generate_python):
        """Numeric coercion handles decimals correctly.

        '3.14ABC' coerces to 3.14.
        """
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestTruthValueCodegen:
    """Codegen tests for MUMPS truth value helper (m_truth).

    Truth in MUMPS is numeric-based: 0 is false, all nonzero is true.
    This affects IF conditions, postconditions, and logical operators.

    Reference: §1.2.4
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: zero is false")
    def test_zero_is_false(self, generate_python):
        """Numeric 0 evaluates to false.

        '0', '', 'A' all coerce to 0 → false.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: nonzero is true")
    def test_nonzero_is_true(self, generate_python):
        """Any nonzero numeric evaluates to true.

        '1', '3.14', '1A', '-5' all coerce to nonzero → true.
        """
        pytest.fail("Stub - implement test")

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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: numeric comparison")
    def test_numeric_comparison(self, generate_python):
        """Less-than/greater-than use numeric coercion.

        '3' < '10' is true (3 < 10), but 'A' < 'B' compares 0 < 0.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: string equality")
    def test_string_equality(self, generate_python):
        """Equality compares string values directly.

        '3' = '03' is false (string comparison), but '3' = 3 needs coercion.
        """
        pytest.fail("Stub - implement test")
