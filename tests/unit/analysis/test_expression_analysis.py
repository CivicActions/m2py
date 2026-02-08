"""Tests for semantic analyzer internal functions.

Tests analyze_expression() and unwrap_expression() internal mechanisms.

"""

from tests.helpers.parsing import parse_expression
from m2py.analysis.semantic_analyzer import analyze_expression, unwrap_expression
from m2py.asg.expressions import (
    MLiteral,
    MVariable,
    MGlobal,
    MNakedGlobal,
    MBinaryOp,
    MUnaryOp,
    MIntrinsicFunction,
    MSpecialVariable,
)
from m2py.asg.enums import LiteralType


class TestAnalyzeExpression:
    """Test analyze_expression function."""

    def test_analyze_simple_literal(self):
        """Test analyzing a numeric literal."""
        expr = parse_expression("42")
        result = analyze_expression(expr)

        assert isinstance(result, MLiteral)
        assert result.value == 42
        assert result.literal_type == LiteralType.INTEGER

    def test_analyze_string_literal(self):
        """Test analyzing a string literal."""
        expr = parse_expression('"hello"')
        result = analyze_expression(expr)

        assert isinstance(result, MLiteral)
        assert result.value == "hello"
        assert result.literal_type == LiteralType.STRING

    def test_analyze_local_variable(self):
        """Test analyzing a local variable."""
        expr = parse_expression("X")
        result = analyze_expression(expr)

        assert isinstance(result, MVariable)
        assert result.name == "X"

    def test_analyze_global_variable(self):
        """Test analyzing a global variable."""
        expr = parse_expression("^GLOBAL")
        result = analyze_expression(expr)

        assert isinstance(result, MGlobal)
        assert result.name == "GLOBAL"

    def test_analyze_binary_operation(self):
        """Test analyzing a binary operation."""
        expr = parse_expression("X+1")
        result = analyze_expression(expr)

        assert isinstance(result, MBinaryOp)
        assert result.operator == "+"
        assert isinstance(result.left, MVariable)
        assert result.left.name == "X"
        assert isinstance(result.right, MLiteral)
        assert result.right.value == 1

    def test_analyze_chained_binary_operations(self):
        """Test analyzing chained binary operations (left-to-right)."""
        expr = parse_expression("1+2*3")
        result = analyze_expression(expr)

        # MUMPS is strictly left-to-right: ((1+2)*3)
        assert isinstance(result, MBinaryOp)
        assert result.operator == "*"
        assert isinstance(result.left, MBinaryOp)
        assert result.left.operator == "+"

    def test_analyze_unary_minus(self):
        """Test analyzing unary minus."""
        expr = parse_expression("-X")
        result = analyze_expression(expr)

        assert isinstance(result, MUnaryOp)
        assert result.operator == "-"
        assert isinstance(result.operand, MVariable)
        assert result.operand.name == "X"

    def test_analyze_special_variable(self):
        """Test analyzing special variable."""
        expr = parse_expression("$TEST")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "TEST"

    def test_analyze_intrinsic_function(self):
        """Test analyzing intrinsic function."""
        expr = parse_expression("$LENGTH(X)")
        result = analyze_expression(expr)

        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "LENGTH"
        assert len(result.arguments) == 1
        assert isinstance(result.arguments[0], MVariable)

    def test_analyze_naked_global(self):
        """Test analyzing naked global reference."""
        expr = parse_expression("^(1,2)")
        result = analyze_expression(expr)

        assert isinstance(result, MNakedGlobal)
        assert len(result.subscripts) == 2
        assert all(isinstance(s, MLiteral) for s in result.subscripts)

    def test_analyze_naked_global_with_negative_subscript(self):
        """Test analyzing naked global with negative subscript - T076 fix.

        This reproduces the bug found in V1NX test where ^(3,-1) caused
        a NotImplementedError because the -1 subscript remained as a raw
        textX UnaryExpr instead of being transformed to MUnaryOp.
        """
        expr = parse_expression("^(3,-1)")
        result = analyze_expression(expr)

        assert isinstance(result, MNakedGlobal)
        assert len(result.subscripts) == 2
        # First subscript is literal 3
        assert isinstance(result.subscripts[0], MLiteral)
        assert result.subscripts[0].value == 3
        # Second subscript is unary minus (not raw UnaryExpr)
        assert isinstance(result.subscripts[1], MUnaryOp)
        assert result.subscripts[1].operator == "-"
        assert isinstance(result.subscripts[1].operand, MLiteral)
        assert result.subscripts[1].operand.value == 1

    def test_analyze_naked_global_with_expression_subscript(self):
        """Test analyzing naked global with expression in subscript."""
        expr = parse_expression("^(X+1)")
        result = analyze_expression(expr)

        assert isinstance(result, MNakedGlobal)
        assert len(result.subscripts) == 1
        assert isinstance(result.subscripts[0], MBinaryOp)
        assert result.subscripts[0].operator == "+"


class TestUnwrapExpression:
    """Test unwrap_expression function."""

    def test_unwrap_already_mexpr(self):
        """Test unwrapping already an MExpr."""
        literal = MLiteral(value=42)
        result = unwrap_expression(literal)
        assert result is literal

    def test_unwrap_none(self):
        """Test unwrapping None."""
        result = unwrap_expression(None)
        assert result is None

    def test_unwrap_textx_expr(self):
        """Test unwrapping textX Expr."""
        expr = parse_expression("X")
        result = unwrap_expression(expr)

        # Should be unwrapped to the LocalVariable custom class
        assert isinstance(result, MVariable)
        assert result.name == "X"
