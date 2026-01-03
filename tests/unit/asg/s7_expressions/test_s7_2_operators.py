"""Tests for Operators ASG analysis (§7.2).

Reference: MUMPS 1995 ANSI Standard, Section 7.2
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.expressions import (
    MLiteral,
    LiteralType,
    MVariable,
    MIntrinsicFunction,
    MBinaryOp,
)


@pytest.mark.asg
class TestOperatorsAnalysis:
    """ASG-level tests for operators analysis (§7.2)."""

    # Unary operators
    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: unary plus")
    def test_unary_plus(self, analyze_expression):
        """Unary plus operator is correctly analyzed (§7.2.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: unary minus")
    def test_unary_minus(self, analyze_expression):
        """Unary minus operator is correctly analyzed (§7.2.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: logical NOT")
    def test_logical_not(self, analyze_expression):
        """Logical NOT operator is correctly analyzed (§7.2.1)."""
        pytest.fail("Stub - implement test")

    # Binary arithmetic operators
    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: addition")
    def test_addition(self, analyze_expression):
        """Addition operator is correctly analyzed (§7.2.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: subtraction")
    def test_subtraction(self, analyze_expression):
        """Subtraction operator is correctly analyzed (§7.2.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: multiplication")
    def test_multiplication(self, analyze_expression):
        """Multiplication operator is correctly analyzed (§7.2.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: division")
    def test_division(self, analyze_expression):
        """Division operator is correctly analyzed (§7.2.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: integer division")
    def test_integer_division(self, analyze_expression):
        """Integer division (\\) operator is correctly analyzed (§7.2.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: modulo")
    def test_modulo(self, analyze_expression):
        """Modulo (#) operator is correctly analyzed (§7.2.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: exponentiation")
    def test_exponentiation(self, analyze_expression):
        """Exponentiation (**) operator is correctly analyzed (§7.2.2)."""
        pytest.fail("Stub - implement test")

    # String operators
    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: concatenation")
    def test_concatenation(self, analyze_expression):
        """Concatenation (_) operator is correctly analyzed (§7.2.3)."""
        pytest.fail("Stub - implement test")

    # Relational operators
    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: equals")
    def test_equals(self, analyze_expression):
        """Equals (=) operator is correctly analyzed (§7.2.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: less than")
    def test_less_than(self, analyze_expression):
        """Less than (<) operator is correctly analyzed (§7.2.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: greater than")
    def test_greater_than(self, analyze_expression):
        """Greater than (>) operator is correctly analyzed (§7.2.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: contains")
    def test_contains(self, analyze_expression):
        """Contains ([) operator is correctly analyzed (§7.2.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: follows")
    def test_follows(self, analyze_expression):
        """Follows (]) operator is correctly analyzed (§7.2.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: sorts after")
    def test_sorts_after(self, analyze_expression):
        """Sorts after (]]) operator is correctly analyzed (§7.2.4)."""
        pytest.fail("Stub - implement test")

    # Logical operators
    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: logical AND")
    def test_logical_and(self, analyze_expression):
        """Logical AND (&) operator is correctly analyzed (§7.2.6)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: logical OR")
    def test_logical_or(self, analyze_expression):
        """Logical OR (!) operator is correctly analyzed (§7.2.6)."""
        pytest.fail("Stub - implement test")

    # Evaluation order
    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: left-to-right evaluation")
    def test_left_to_right_evaluation(self, analyze_expression):
        """Left-to-right evaluation order is maintained (§7.2)."""
        pytest.fail("Stub - implement test")


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestExpressionAnalysisInContext:
    """Tests for expression analysis within commands."""

    def test_numeric_literal_integer(self):
        """Integer numeric literal."""
        stmt = analyze_first_command("S X=42")

        value = stmt.assignments[0].value
        assert isinstance(value, MLiteral)
        assert value.literal_type == LiteralType.INTEGER
        assert value.value == 42

    def test_numeric_literal_decimal(self):
        """Decimal numeric literal."""
        stmt = analyze_first_command("S X=3.14")

        value = stmt.assignments[0].value
        assert isinstance(value, MLiteral)
        assert value.literal_type == LiteralType.DECIMAL
        assert value.value == 3.14

    def test_variable_with_subscripts(self):
        """Variable with subscripts."""
        stmt = analyze_first_command("S X(1,2)=3")

        target = stmt.assignments[0].target
        assert isinstance(target, MVariable)
        assert target.name == "X"
        assert len(target.subscripts) == 2

    def test_intrinsic_function(self):
        """Intrinsic function call."""
        stmt = analyze_first_command('S X=$L("hello")')

        value = stmt.assignments[0].value
        assert isinstance(value, MIntrinsicFunction)
        assert value.name == "L"
        assert len(value.arguments) == 1

    def test_binary_expression(self):
        """Binary expression in assignment."""
        stmt = analyze_first_command("S X=A+B")

        value = stmt.assignments[0].value
        assert isinstance(value, MBinaryOp)
        assert value.operator == "+"
        assert isinstance(value.left, MVariable)
        assert isinstance(value.right, MVariable)
