"""Tests for Operators ASG analysis (§7.2).

Reference: MUMPS 1995 ANSI Standard, Section 7.2

Key operator categories (from 1977__a107192-199, 1995__a901001):
- Unary: + (plus), - (negate), ' (NOT)
- Binary arithmetic: + - * / \\ # **
- Binary relational: = < > [ ] ]]
- Binary logical: & !
- Binary string: _ (concatenate)

MUMPS evaluates strictly left-to-right with no operator precedence.
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
    MUnaryOp,
)
from m2py.parser.textx_classes import NumericLiteral, LocalVariable


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


def get_expression_from_set(line: str):
    """Helper to get the value expression from a SET command."""
    stmt = analyze_first_command(line)
    return stmt.assignments[0].value


@pytest.mark.asg
class TestOperatorsAnalysis:
    """ASG-level tests for operators analysis (§7.2)."""

    # Unary operators (§7.2.1)

    def test_unary_plus(self):
        """Unary plus operator is correctly analyzed (§7.2.1).

        From spec: Unary plus produces the numeric interpretation of its operand.
        """
        value = get_expression_from_set("S X=+Y")

        assert isinstance(value, MUnaryOp)
        assert value.operator == "+"
        assert isinstance(value.operand, LocalVariable)
        assert value.operand.name == "Y"

    def test_unary_minus(self):
        """Unary minus operator is correctly analyzed (§7.2.1).

        From spec: Unary minus produces the arithmetic negation.
        """
        value = get_expression_from_set("S X=-5")

        assert isinstance(value, MUnaryOp)
        assert value.operator == "-"
        # Operand is the literal 5
        assert isinstance(value.operand, NumericLiteral)
        assert value.operand.value == 5

    def test_logical_not(self):
        """Logical NOT operator is correctly analyzed (§7.2.1).

        From spec: The unary logical operator ' (NOT) produces the
        truth-value complement.
        """
        value = get_expression_from_set("S X='Y")

        assert isinstance(value, MUnaryOp)
        assert value.operator == "'"
        assert isinstance(value.operand, LocalVariable)
        assert value.operand.name == "Y"

    # Binary arithmetic operators (§7.2.2)

    def test_addition(self):
        """Addition operator is correctly analyzed (§7.2.2).

        From spec (1977__a107193): + produces the algebraic sum.
        """
        value = get_expression_from_set("S X=A+B")

        assert isinstance(value, MBinaryOp)
        assert value.operator == "+"
        assert isinstance(value.left, LocalVariable)
        assert isinstance(value.right, LocalVariable)
        assert value.left.name == "A"
        assert value.right.name == "B"

    def test_subtraction(self):
        """Subtraction operator is correctly analyzed (§7.2.2).

        From spec (1977__a107193): - produces the algebraic difference.
        """
        value = get_expression_from_set("S X=A-B")

        assert isinstance(value, MBinaryOp)
        assert value.operator == "-"
        assert isinstance(value.left, LocalVariable)
        assert isinstance(value.right, LocalVariable)

    def test_multiplication(self):
        """Multiplication operator is correctly analyzed (§7.2.2).

        From spec (1977__a107193): * produces the algebraic product.
        """
        value = get_expression_from_set("S X=A*B")

        assert isinstance(value, MBinaryOp)
        assert value.operator == "*"
        assert isinstance(value.left, LocalVariable)
        assert isinstance(value.right, LocalVariable)

    def test_division(self):
        """Division operator is correctly analyzed (§7.2.2).

        From spec (1977__a107193): / produces the algebraic quotient.
        """
        value = get_expression_from_set("S X=A/B")

        assert isinstance(value, MBinaryOp)
        assert value.operator == "/"
        assert isinstance(value.left, LocalVariable)
        assert isinstance(value.right, LocalVariable)

    def test_integer_division(self):
        """Integer division (\\) operator is correctly analyzed (§7.2.2).

        From spec (1977__a107193): \\ produces the integer interpretation
        of the result of division.
        """
        value = get_expression_from_set("S X=A\\B")

        assert isinstance(value, MBinaryOp)
        assert value.operator == "\\"
        assert isinstance(value.left, LocalVariable)
        assert isinstance(value.right, LocalVariable)

    def test_modulo(self):
        """Modulo (#) operator is correctly analyzed (§7.2.2).

        From spec (1977__a107193): A#B = A - (B * floor(A/B))
        """
        value = get_expression_from_set("S X=A#B")

        assert isinstance(value, MBinaryOp)
        assert value.operator == "#"
        assert isinstance(value.left, LocalVariable)
        assert isinstance(value.right, LocalVariable)

    def test_exponentiation(self):
        """Exponentiation (**) operator is correctly analyzed (§7.2.2).

        Multi-character operator for raising to a power.
        """
        value = get_expression_from_set("S X=A**B")

        assert isinstance(value, MBinaryOp)
        assert value.operator == "**"
        assert isinstance(value.left, LocalVariable)
        assert isinstance(value.right, LocalVariable)

    # String operators (§7.2.3)

    def test_concatenation(self):
        """Concatenation (_) operator is correctly analyzed (§7.2.3).

        From spec (1977__a107192): The underscore _ is the concatenation
        operator. The value of A_B is the string obtained by concatenating
        the values of A and B, with A on the left.
        """
        value = get_expression_from_set("S X=A_B")

        assert isinstance(value, MBinaryOp)
        assert value.operator == "_"
        assert isinstance(value.left, LocalVariable)
        assert isinstance(value.right, LocalVariable)

    # Relational operators (§7.2.4)

    def test_equals(self):
        """Equals (=) operator is correctly analyzed (§7.2.4).

        From spec (1977__a107197): The relation = tests string identity.
        """
        value = get_expression_from_set("S X=A=B")

        assert isinstance(value, MBinaryOp)
        assert value.operator == "="
        assert isinstance(value.left, LocalVariable)
        assert isinstance(value.right, LocalVariable)

    def test_less_than(self):
        """Less than (<) operator is correctly analyzed (§7.2.4).

        From spec (1977__a107196): < denotes the conventional algebraic
        "less than".
        """
        value = get_expression_from_set("S X=A<B")

        assert isinstance(value, MBinaryOp)
        assert value.operator == "<"
        assert isinstance(value.left, LocalVariable)
        assert isinstance(value.right, LocalVariable)

    def test_greater_than(self):
        """Greater than (>) operator is correctly analyzed (§7.2.4).

        From spec (1977__a107196): > denotes the conventional algebraic
        "greater than".
        """
        value = get_expression_from_set("S X=A>B")

        assert isinstance(value, MBinaryOp)
        assert value.operator == ">"
        assert isinstance(value.left, LocalVariable)
        assert isinstance(value.right, LocalVariable)

    def test_contains(self):
        """Contains ([) operator is correctly analyzed (§7.2.4).

        From spec (1977__a107197): A[B is true if and only if B is a
        substring of A.
        """
        value = get_expression_from_set("S X=A[B")

        assert isinstance(value, MBinaryOp)
        assert value.operator == "["
        assert isinstance(value.left, LocalVariable)
        assert isinstance(value.right, LocalVariable)

    def test_follows(self):
        """Follows (]) operator is correctly analyzed (§7.2.4).

        From spec (1977__a107197): A]B is true if and only if A follows B
        in the conventional ASCII collating sequence.
        """
        value = get_expression_from_set("S X=A]B")

        assert isinstance(value, MBinaryOp)
        assert value.operator == "]"
        assert isinstance(value.left, LocalVariable)
        assert isinstance(value.right, LocalVariable)

    def test_sorts_after(self):
        """Sorts after (]]) operator is correctly analyzed (§7.2.4).

        From spec (1995__a901001): ]] is the "collates after" operator.
        Distinct from ] (follows) - returns true if left operand sorts
        after right in subscript collation order.
        """
        value = get_expression_from_set("S X=A]]B")

        assert isinstance(value, MBinaryOp)
        assert value.operator == "]]"
        assert isinstance(value.left, LocalVariable)
        assert isinstance(value.right, LocalVariable)

    # Logical operators (§7.2.6)

    def test_logical_and(self):
        """Logical AND (&) operator is correctly analyzed (§7.2.6).

        From spec (1977__a107198): A&B = 1 if both A and B have value 1,
        0 otherwise.
        """
        value = get_expression_from_set("S X=A&B")

        assert isinstance(value, MBinaryOp)
        assert value.operator == "&"
        assert isinstance(value.left, LocalVariable)
        assert isinstance(value.right, LocalVariable)

    def test_logical_or(self):
        """Logical OR (!) operator is correctly analyzed (§7.2.6).

        From spec (1977__a107198): A!B = 0 if both A and B have value 0,
        1 otherwise.
        """
        value = get_expression_from_set("S X=A!B")

        assert isinstance(value, MBinaryOp)
        assert value.operator == "!"
        assert isinstance(value.left, LocalVariable)
        assert isinstance(value.right, LocalVariable)

    # Evaluation order

    def test_left_to_right_evaluation(self):
        """Left-to-right evaluation order is maintained (§7.2).

        From spec (1995__a901001): MUMPS evaluates strictly from left
        to right, so 1+1*2 yields 4 and not 3.

        The expression 1+2*3 should be parsed as ((1+2)*3) = 9
        NOT as 1+(2*3) = 7 (standard math precedence).
        """
        value = get_expression_from_set("S X=1+2*3")

        # Top-level should be multiplication (last operation)
        assert isinstance(value, MBinaryOp)
        assert value.operator == "*"

        # Left side should be the addition (1+2)
        assert isinstance(value.left, MBinaryOp)
        assert value.left.operator == "+"

        # Right side is the literal 3
        assert isinstance(value.right, NumericLiteral)
        assert value.right.value == 3

        # Verify the nested addition operands
        assert isinstance(value.left.left, NumericLiteral)
        assert value.left.left.value == 1
        assert isinstance(value.left.right, NumericLiteral)
        assert value.left.right.value == 2


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
