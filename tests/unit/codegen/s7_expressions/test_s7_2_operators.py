"""Tests for Operators code generation (§7.2).

Reference: MUMPS 1995 ANSI Standard, Section 7.2
"""

import pytest


@pytest.mark.codegen
class TestOperatorsCodegen:
    """Codegen-level tests for operators code generation (§7.2)."""

    def test_addition(self, execute_mumps):
        """Addition generates Python + with numeric coercion (§7.2).

        User Story 1 acceptance scenario 3:
        Given: TEST W 2+3 Q
        When: generated and executed
        Then: output is "5"
        """
        result = execute_mumps("TEST\n W 2+3\n Q\n")
        assert result.output == "5"
        assert result.success is True

    def test_subtraction(self, execute_mumps):
        """Subtraction generates Python - with numeric coercion (§7.2)."""
        result = execute_mumps("TEST\n W 5-3\n Q\n")
        assert result.output == "2"
        assert result.success is True

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: multiplication")
    def test_multiplication(self, generate_python):
        """Multiplication generates Python * with numeric coercion (§7.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: division")
    def test_division(self, generate_python):
        """Division generates Python / with numeric coercion (§7.2)."""
        pytest.fail("Stub - implement test")

    def test_integer_division(self, execute_mumps):
        """Integer division generates Python int(x/y) for truncation (§7.2).

        User Story 5 acceptance scenario 2:
        YDB verified: 7\3 → 2
        """
        result = execute_mumps("TEST\n W 7\\3\n Q\n")
        assert result.output == "2"
        assert result.success is True

    def test_integer_division_second(self, execute_mumps):
        """Integer division acceptance scenario 4.

        YDB verified: 10\4 → 2
        """
        result = execute_mumps("TEST\n W 10\\4\n Q\n")
        assert result.output == "2"
        assert result.success is True

    def test_integer_division_negative(self, execute_mumps):
        """Integer division with negative number uses truncation towards zero.

        YDB verified: -7\3 → -2 (not -3 as floor division would give)
        """
        result = execute_mumps("TEST\n W -7\\3\n Q\n")
        assert result.output == "-2"
        assert result.success is True

    def test_modulo(self, execute_mumps):
        """Modulo generates Python % (§7.2).

        User Story 5 acceptance scenario 1:
        YDB verified: 7#3 → 1
        """
        result = execute_mumps("TEST\n W 7#3\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_modulo_second(self, execute_mumps):
        """Modulo acceptance scenario 3.

        YDB verified: 10#4 → 2
        """
        result = execute_mumps("TEST\n W 10#4\n Q\n")
        assert result.output == "2"
        assert result.success is True

    def test_modulo_negative_dividend(self, execute_mumps):
        """Modulo with negative dividend.

        YDB verified: -7#3 → 2
        """
        result = execute_mumps("TEST\n W -7#3\n Q\n")
        assert result.output == "2"
        assert result.success is True

    def test_modulo_zero_dividend(self, execute_mumps):
        """Modulo with zero dividend.

        YDB verified: 0#5 → 0
        """
        result = execute_mumps("TEST\n W 0#5\n Q\n")
        assert result.output == "0"
        assert result.success is True

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: exponentiation")
    def test_exponentiation(self, generate_python):
        """Exponentiation generates Python ** (§7.2)."""
        pytest.fail("Stub - implement test")

    def test_concatenation_strings(self, execute_mumps):
        """Concatenation joins strings correctly (§7.2).

        YDB verified: "A"_"B"_"C" → "ABC"
        """
        result = execute_mumps('TEST\n W "A"_"B"_"C"\n Q\n')
        assert result.output == "ABC"
        assert result.success is True

    def test_concatenation_with_number(self, execute_mumps):
        """Concatenation coerces numbers to strings (§7.2).

        YDB verified: "X"_1_"Y" → "X1Y"
        """
        result = execute_mumps('TEST\n W "X"_1_"Y"\n Q\n')
        assert result.output == "X1Y"
        assert result.success is True

    def test_concatenation_with_variable(self, execute_mumps):
        """Concatenation works with variables (§7.2).

        YDB verified: S X="Hello" W X_" World" → "Hello World"
        """
        result = execute_mumps('TEST\n S X="Hello" W X_" World"\n Q\n')
        assert result.output == "Hello World"
        assert result.success is True

    def test_concatenation_numbers_only(self, execute_mumps):
        """Concatenation of numbers coerces all to strings (§7.2).

        YDB verified: 1_2_3 → "123"
        """
        result = execute_mumps("TEST\n W 1_2_3\n Q\n")
        assert result.output == "123"
        assert result.success is True

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: equals comparison")
    def test_equals(self, generate_python):
        """Equals generates Python == (§7.2)."""
        pytest.fail("Stub - implement test")

    # =========================================================================
    # Negated Comparison Operators Tests
    # =========================================================================

    def test_negated_equals_same_value(self, execute_mumps):
        """Negated equals returns 0 for equal values (§7.2).

        YDB verified: 5'=5 → 0
        """
        result = execute_mumps("TEST\n W 5'=5\n Q\n")
        assert result.output == "0"
        assert result.success is True

    def test_negated_equals_different_values(self, execute_mumps):
        """Negated equals returns 1 for different values (§7.2).

        YDB verified: 5'=6 → 1
        """
        result = execute_mumps("TEST\n W 5'=6\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_negated_less_than(self, execute_mumps):
        """Negated less-than (>=) returns correct value (§7.2).

        YDB verified: 10'<5 → 1 (10 is not less than 5)
        """
        result = execute_mumps("TEST\n W 10'<5\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_negated_greater_than(self, execute_mumps):
        """Negated greater-than (<=) returns correct value (§7.2).

        YDB verified: 5'>10 → 1 (5 is not greater than 10)
        """
        result = execute_mumps("TEST\n W 5'>10\n Q\n")
        assert result.output == "1"
        assert result.success is True

    # =========================================================================
    # Contains and Follows Operators Tests (Spec 011 Phase 10)
    # =========================================================================

    def test_contains_match(self, execute_mumps):
        """Contains operator returns 1 when substring found (§7.2).

        YDB verified: "ABC"["B" → 1
        """
        result = execute_mumps('TEST\n W "ABC"["B"\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_contains_no_match(self, execute_mumps):
        """Contains operator returns 0 when substring not found (§7.2).

        YDB verified: "ABC"["X" → 0
        """
        result = execute_mumps('TEST\n W "ABC"["X"\n Q\n')
        assert result.output == "0"
        assert result.success is True

    def test_contains_empty_string(self, execute_mumps):
        """Contains operator: empty string is in any string (§7.2).

        YDB verified: "ABC"["" → 1
        """
        result = execute_mumps('TEST\n W "ABC"[""\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_follows_true(self, execute_mumps):
        """Follows operator returns 1 when left sorts after right (§7.2).

        YDB verified: "B"]"A" → 1
        """
        result = execute_mumps('TEST\n W "B"]"A"\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_follows_false(self, execute_mumps):
        """Follows operator returns 0 when left does not sort after right (§7.2).

        YDB verified: "A"]"B" → 0
        """
        result = execute_mumps('TEST\n W "A"]"B"\n Q\n')
        assert result.output == "0"
        assert result.success is True

    def test_sorts_after_true(self, execute_mumps):
        """Sorts-after operator returns 1 when left strictly sorts after right (§7.2).

        YDB verified: "B"]]"A" → 1
        """
        result = execute_mumps('TEST\n W "B"]]"A"\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_sorts_after_same_value(self, execute_mumps):
        """Sorts-after operator returns 0 for equal values (§7.2).

        YDB verified: "A"]]"A" → 0
        """
        result = execute_mumps('TEST\n W "A"]]"A"\n Q\n')
        assert result.output == "0"
        assert result.success is True

    def test_sorts_after_empty_string(self, execute_mumps):
        """Sorts-after: empty string never sorts after anything (§7.2).

        YDB verified: ""]]"A" → 0
        """
        result = execute_mumps('TEST\n W ""]]"A"\n Q\n')
        assert result.output == "0"
        assert result.success is True

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: logical AND")
    def test_logical_and(self, generate_python):
        """Logical AND generates Python and (§7.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: logical OR")
    def test_logical_or(self, generate_python):
        """Logical OR generates Python or (§7.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: left-to-right evaluation")
    def test_left_to_right_evaluation(self, generate_python):
        """Left-to-right evaluation is preserved (§7.2)."""
        pytest.fail("Stub - implement test")
