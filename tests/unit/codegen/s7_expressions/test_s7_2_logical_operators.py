"""Tests for Logical Operators code generation (§7.2).

Reference: MUMPS 1995 ANSI Standard, Section 7.2

Tests the three MUMPS logical operators:
- & (AND): Returns 1 if both operands are true, 0 otherwise
- ! (OR): Returns 1 if either operand is true, 0 otherwise
- ' (NOT): Returns 0 if operand is true, 1 if false

MUMPS uses 0/1 for boolean values (not Python True/False).
Truth evaluation: 0 and "" are false, all other values are true.
"""

import pytest


@pytest.mark.codegen
class TestLogicalOperatorsCodegen:
    """Codegen-level tests for logical operators code generation (§7.2).

    Tests verify correct 0/1 output for MUMPS logical operators.
    """

    # =========================================================================
    # NOT Operator (') Tests
    # =========================================================================

    def test_not_true_returns_zero(self, execute_mumps):
        """NOT of true value returns 0 (§7.2).

        YDB verified: W '1 → 0
        """
        result = execute_mumps("TEST\n W '1\n Q\n")
        assert result.output == "0"
        assert result.success is True

    def test_not_false_returns_one(self, execute_mumps):
        """NOT of false value returns 1 (§7.2).

        YDB verified: W '0 → 1
        """
        result = execute_mumps("TEST\n W '0\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_not_string_empty_returns_one(self, execute_mumps):
        """NOT of empty string returns 1 (§7.2).

        Empty string is falsy in MUMPS.
        YDB verified: W '\"\" → 1
        """
        result = execute_mumps('TEST\n W \'""\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_not_nonzero_string_returns_zero(self, execute_mumps):
        """NOT of string starting with nonzero returns 0 (§7.2).

        Strings are coerced to numbers for truth evaluation.
        YDB verified: W '"5ABC" → 0 (5 is truthy)
        """
        result = execute_mumps('TEST\n W \'"5ABC"\n Q\n')
        assert result.output == "0"
        assert result.success is True

    # =========================================================================
    # AND Operator (&) Tests
    # =========================================================================

    def test_and_true_true_returns_one(self, execute_mumps):
        """AND of two true values returns 1 (§7.2).

        YDB verified: W 1&1 → 1
        """
        result = execute_mumps("TEST\n W 1&1\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_and_true_false_returns_zero(self, execute_mumps):
        """AND of true and false returns 0 (§7.2).

        YDB verified: W 1&0 → 0
        """
        result = execute_mumps("TEST\n W 1&0\n Q\n")
        assert result.output == "0"
        assert result.success is True

    def test_and_false_false_returns_zero(self, execute_mumps):
        """AND of two false values returns 0 (§7.2).

        YDB verified: W 0&0 → 0
        """
        result = execute_mumps("TEST\n W 0&0\n Q\n")
        assert result.output == "0"
        assert result.success is True

    def test_and_false_true_returns_zero(self, execute_mumps):
        """AND of false and true returns 0 (§7.2).

        YDB verified: W 0&1 → 0
        """
        result = execute_mumps("TEST\n W 0&1\n Q\n")
        assert result.output == "0"
        assert result.success is True

    # =========================================================================
    # OR Operator (!) Tests
    # =========================================================================

    def test_or_true_true_returns_one(self, execute_mumps):
        """OR of two true values returns 1 (§7.2).

        YDB verified: W 1!1 → 1
        """
        result = execute_mumps("TEST\n W 1!1\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_or_true_false_returns_one(self, execute_mumps):
        """OR of true and false returns 1 (§7.2).

        YDB verified: W 1!0 → 1
        """
        result = execute_mumps("TEST\n W 1!0\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_or_false_true_returns_one(self, execute_mumps):
        """OR of false and true returns 1 (§7.2).

        YDB verified: W 0!1 → 1
        """
        result = execute_mumps("TEST\n W 0!1\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_or_false_false_returns_zero(self, execute_mumps):
        """OR of two false values returns 0 (§7.2).

        YDB verified: W 0!0 → 0
        """
        result = execute_mumps("TEST\n W 0!0\n Q\n")
        assert result.output == "0"
        assert result.success is True

    # =========================================================================
    # Left-to-Right Evaluation Tests
    # =========================================================================

    def test_left_to_right_and_or(self, execute_mumps):
        """Operators evaluate left-to-right without precedence (§7.2).

        MUMPS: 1!0&0 = (1!0)&0 = 1&0 = 0
        NOT: 1!(0&0) = 1!0 = 1 (C/Python precedence)

        YDB verified: W 1!0&0 → 0
        """
        result = execute_mumps("TEST\n W 1!0&0\n Q\n")
        assert result.output == "0"
        assert result.success is True

    def test_left_to_right_arithmetic_and_logical(self, execute_mumps):
        """Arithmetic and logical operators evaluate left-to-right (§7.2).

        MUMPS: 2+3&1 = (2+3)&1 = 5&1 = 1 (5 is truthy)

        YDB verified: W 2+3&1 → 1
        """
        result = execute_mumps("TEST\n W 2+3&1\n Q\n")
        assert result.output == "1"
        assert result.success is True
