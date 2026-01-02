"""Tests for Values ASG analysis (§7.1.1).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.1

Migrated from: tests/unit/test_semantic_analyzer.py::TestAnalyzeExpression (partial)
"""

import pytest
from tests.helpers.parsing import parse_expression
from m2py.analysis.semantic_analyzer import analyze_expression
from m2py.asg.expressions import MLiteral, MBinaryOp, MUnaryOp, MVariable
from m2py.asg.enums import LiteralType


@pytest.mark.asg
class TestValuesAnalysis:
    """ASG-level tests for values analysis (§7.1.1).

    Migrated from: TestAnalyzeExpression
    """

    def test_analyze_simple_literal(self):
        """Numeric literal analysis produces MLiteral with INTEGER type (§7.1.1)."""
        expr = parse_expression("42")
        result = analyze_expression(expr)

        assert isinstance(result, MLiteral)
        assert result.value == 42
        assert result.literal_type == LiteralType.INTEGER

    def test_analyze_string_literal(self):
        """String literal analysis produces MLiteral with STRING type (§7.1.1)."""
        expr = parse_expression('"hello"')
        result = analyze_expression(expr)

        assert isinstance(result, MLiteral)
        assert result.value == "hello"
        assert result.literal_type == LiteralType.STRING

    def test_analyze_binary_operation(self):
        """Binary operation analysis produces MBinaryOp node (§7.1.1)."""
        expr = parse_expression("X+1")
        result = analyze_expression(expr)

        assert isinstance(result, MBinaryOp)
        assert result.operator == "+"
        assert isinstance(result.left, MVariable)
        assert result.left.name == "X"
        assert isinstance(result.right, MLiteral)
        assert result.right.value == 1

    def test_analyze_chained_binary_operations(self):
        """Chained binary operations are left-to-right per MUMPS spec (§7.1.1)."""
        expr = parse_expression("1+2*3")
        result = analyze_expression(expr)

        # MUMPS is strictly left-to-right: ((1+2)*3)
        assert isinstance(result, MBinaryOp)
        assert result.operator == "*"
        assert isinstance(result.left, MBinaryOp)
        assert result.left.operator == "+"

    def test_analyze_unary_minus(self):
        """Unary minus analysis produces MUnaryOp node (§7.1.1)."""
        expr = parse_expression("-X")
        result = analyze_expression(expr)

        assert isinstance(result, MUnaryOp)
        assert result.operator == "-"
        assert isinstance(result.operand, MVariable)
        assert result.operand.name == "X"
