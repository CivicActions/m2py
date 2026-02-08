"""Tests for Values code generation (§7.1.1).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.1
"""

import pytest


@pytest.mark.codegen
class TestValuesCodegen:
    """Codegen-level tests for values code generation (§7.1.1)."""

    def test_string_value(self, execute_mumps):
        """String values output directly (§7.1.1).

        YDB verified: W "hello" → "hello"
        """
        result = execute_mumps('TEST\n W "hello"\n Q\n')
        assert result.output == "hello"
        assert result.success is True

    def test_numeric_value(self, execute_mumps):
        """Numeric values output directly (§7.1.1).

        YDB verified: W 42 → "42"
        """
        result = execute_mumps("TEST\n W 42\n Q\n")
        assert result.output == "42"
        assert result.success is True

    def test_empty_string(self, execute_mumps):
        """Empty string outputs nothing (§7.1.1).

        YDB verified: W "" → ""
        """
        result = execute_mumps('TEST\n W ""\n Q\n')
        assert result.output == ""
        assert result.success is True

    def test_mvalue_wrapper(self, execute_mumps):
        """Values handle numeric string coercion correctly (§7.1.1).

        M2py uses helpers (m_num, m_str) rather than MValue class.
        YDB verified: W "3"+2 → "5" (string "3" coerces to numeric 3)
        """
        result = execute_mumps('TEST\n W "3"+2\n Q\n')
        assert result.output == "5"
        assert result.success is True


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

    def test_numeric_prefix_extraction(self):
        """Numeric coercion extracts leading numeric prefix (§7.1.4.5).

        m_num('3A') returns 3, m_num('A3') returns 0.
        """
        from m2py.codegen.helpers import m_num

        assert m_num("3A") == 3
        assert m_num("A3") == 0

    def test_empty_string_to_zero(self):
        """Empty string coerces to 0 (§7.1.4.5).

        m_num('') returns 0 per MUMPS semantics.
        """
        from m2py.codegen.helpers import m_num

        assert m_num("") == 0

    def test_sign_canonicalization(self):
        """Numeric coercion canonicalizes signs.

        Phase 10 validation: Test sign handling edge cases.
        '+42' coerces to 42, '--5' coerces to 5, '+-5' coerces to -5.
        NOTE: Leading whitespace makes a string non-numeric in MUMPS!
        '  +42' → 0 (space is non-numeric, stops parsing immediately)
        """
        from m2py.codegen.helpers import m_num

        # Positive sign
        assert m_num("+42") == 42
        # Double negative
        assert m_num("--5") == 5
        # Mixed signs
        assert m_num("+-5") == -5
        assert m_num("-+5") == -5
        # Leading whitespace with sign - CRITICAL: whitespace makes it non-numeric!
        assert m_num("  +42") == 0  # Space is first char, not numeric
        # Just signs (no digits)
        assert m_num("++") == 0
        assert m_num("-") == 0

    def test_decimal_handling(self):
        """Numeric coercion handles decimals correctly.

        Phase 10 validation: Test decimal number parsing.
        '3.14ABC' coerces to Decimal('3.14'), '.5' coerces to Decimal('0.5').
        m_num returns Decimal for decimal strings to preserve precision.
        """
        from decimal import Decimal

        from m2py.codegen.helpers import m_num

        # Decimal with trailing text
        assert m_num("3.14ABC") == Decimal("3.14")
        # Leading decimal
        assert m_num(".5") == Decimal("0.5")
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

    def test_string_with_leading_number(self):
        """String with leading number uses numeric truth (§1.2.4).

        m_truth('1ABC') is True (coerces to 1), m_truth('0ABC') is False.
        """
        from m2py.codegen.helpers import m_truth

        assert m_truth("1ABC") is True
        assert m_truth("0ABC") is False


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
        NOTE: m_compare returns int (0 or 1) per MUMPS semantics, not Python bool.
        """
        from m2py.codegen.helpers import m_compare

        assert m_compare("3", "<", "10") == 1  # 3 < 10
        assert m_compare("3", ">", "10") == 0  # 3 > 10 is false
        assert m_compare("A", "<", "B") == 0  # 0 < 0 is false
        assert m_compare("3A", "<", 5) == 1  # 3 < 5

    def test_string_equality(self):
        """Equality compares string values directly.

        Phase 10 validation: '3' = '03' is false (string comparison).
        NOTE: m_compare returns int (0 or 1) per MUMPS semantics, not Python bool.
        """
        from m2py.codegen.helpers import m_compare

        assert m_compare("3", "=", "3") == 1
        assert m_compare("3", "=", "03") == 0  # String comparison
        assert m_compare(3, "=", 3) == 1

    def test_invalid_operator_raises(self):
        """Invalid comparison operator raises ValueError.

        Phase 10 validation: Cover error path.
        """
        import pytest
        from m2py.codegen.helpers import m_compare

        with pytest.raises(ValueError, match="Unsupported comparison operator"):
            m_compare(1, "!=", 2)


@pytest.mark.codegen
class TestExtrinsicFunctionCodegen:
    """Codegen tests for extrinsic function calls ($$label).

    Extrinsic functions are called with $$ prefix and return values.
    They also stack $TEST - the caller's $TEST is saved before the call
    and restored after, so changes to $TEST inside the extrinsic don't
    leak back to the caller.

    Reference: MUMPS 1995 §8.1.8
    """

    def test_extrinsic_returns_value(self, execute_mumps):
        """Extrinsic function returns its QUIT value.

        T066: $$GETVAL returns the value from QUIT.
        Validated against YottaDB: W $$GETVAL() outputs 42.
        """
        source = """TEST I 1 W $$GETVAL() Q
GETVAL() Q 42"""
        result = execute_mumps(source)

        assert result.output == "42"

    def test_extrinsic_isolates_test(self, execute_mumps):
        """Extrinsic function $TEST changes don't leak to caller.

        T067: $TEST stacking for extrinsic functions.
        Validated against YottaDB: output is '111' (1 before, 1 return, 1 after).

        This verifies that even though SETF contains 'I 0' which sets $TEST=0
        inside the extrinsic, the caller still sees $TEST=1 after the call.
        """
        # Multi-line routine: SETF contains IF 0 to set $TEST=0 internally
        source = """TEST I 1 W $T,$$SETF(),$T Q
SETF()
 I 0
 Q 1"""
        result = execute_mumps(source)

        # Output should be "111":
        # - First $T is 1 (from IF 1)
        # - $$SETF() returns 1
        # - Second $T is 1 (restored, even though SETF did IF 0)
        assert result.output == "111"

    def test_extrinsic_with_arguments(self, execute_mumps):
        """Extrinsic function receives arguments.

        T066: $$ADD(X,Y) receives arguments by value.
        Validated against YottaDB.
        """
        source = """TEST S A=3,B=4 W $$ADD(A,B) Q
ADD(X,Y) Q X+Y"""
        result = execute_mumps(source)

        assert result.output == "7"
