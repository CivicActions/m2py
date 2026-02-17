"""Tests for the expression-level type inference pass.

Tests cover:
- Bottom-up type inference for all expression node types
- Operator result types (arithmetic, comparison, logical, concat)
- Intrinsic function result types
- Special variable result types
- Integration with the codegen pipeline
"""

from __future__ import annotations

import pytest

from m2py.asg.enums import ExprResultType, LiteralType
from m2py.asg.expressions import (
    MBinaryOp,
    MExternalFunction,
    MExtrinsicFunction,
    MGlobal,
    MIndirection,
    MIntrinsicFunction,
    MLiteral,
    MNakedGlobal,
    MPatternMatch,
    MSpecialVariable,
    MStructuredSystemVariable,
    MUnaryOp,
    MVariable,
)
from m2py.analysis.type_inference import _infer_expr, infer_expression_types
from m2py.parser import MUMPSParser


def _parse(code: str):
    """Helper to parse MUMPS code and return the routine."""
    parser = MUMPSParser()
    return parser.parse(code)


@pytest.mark.codegen
class TestInferExprLiterals:
    """Test type inference for literal expressions."""

    def test_string_literal(self):
        node = MLiteral(value="Hello", literal_type=LiteralType.STRING)
        assert _infer_expr(node) == ExprResultType.STRING

    def test_integer_literal(self):
        node = MLiteral(value=42, literal_type=LiteralType.INTEGER)
        assert _infer_expr(node) == ExprResultType.NUMERIC

    def test_decimal_literal(self):
        node = MLiteral(value=3.14, literal_type=LiteralType.DECIMAL)
        assert _infer_expr(node) == ExprResultType.NUMERIC


@pytest.mark.codegen
class TestInferExprVariables:
    """Test type inference for variable references."""

    def test_local_variable(self):
        node = MVariable(name="X", subscripts=[])
        assert _infer_expr(node) == ExprResultType.UNKNOWN

    def test_global_variable(self):
        node = MGlobal(name="GLO", subscripts=[], environment=None)
        assert _infer_expr(node) == ExprResultType.UNKNOWN

    def test_naked_global(self):
        node = MNakedGlobal(subscripts=[])
        assert _infer_expr(node) == ExprResultType.UNKNOWN


@pytest.mark.codegen
class TestInferExprBinaryOps:
    """Test type inference for binary operators."""

    def test_concat_operator(self):
        left = MLiteral(value="a", literal_type=LiteralType.STRING)
        right = MLiteral(value="b", literal_type=LiteralType.STRING)
        node = MBinaryOp(left=left, operator="_", right=right)
        assert _infer_expr(node) == ExprResultType.STRING

    def test_arithmetic_operators(self):
        left = MLiteral(value=1, literal_type=LiteralType.INTEGER)
        right = MLiteral(value=2, literal_type=LiteralType.INTEGER)

        for op in ["+", "-", "*", "/", "\\", "#", "**"]:
            node = MBinaryOp(left=left, operator=op, right=right)
            assert _infer_expr(node) == ExprResultType.NUMERIC, f"Failed for {op}"

    def test_comparison_operators(self):
        left = MLiteral(value=1, literal_type=LiteralType.INTEGER)
        right = MLiteral(value=2, literal_type=LiteralType.INTEGER)

        for op in ["=", "<", ">", "'=", "'<", "'>", "[", "]", "]]"]:
            node = MBinaryOp(left=left, operator=op, right=right)
            assert _infer_expr(node) == ExprResultType.BOOLEAN_INT, f"Failed for {op}"

    def test_logical_operators(self):
        left = MLiteral(value=1, literal_type=LiteralType.INTEGER)
        right = MLiteral(value=0, literal_type=LiteralType.INTEGER)

        for op in ["&", "!"]:
            node = MBinaryOp(left=left, operator=op, right=right)
            assert _infer_expr(node) == ExprResultType.BOOLEAN_INT, f"Failed for {op}"


@pytest.mark.codegen
class TestInferExprUnaryOps:
    """Test type inference for unary operators."""

    def test_not_operator(self):
        operand = MLiteral(value=1, literal_type=LiteralType.INTEGER)
        node = MUnaryOp(operator="'", operand=operand)
        assert _infer_expr(node) == ExprResultType.BOOLEAN_INT

    def test_unary_plus(self):
        operand = MLiteral(value="123", literal_type=LiteralType.STRING)
        node = MUnaryOp(operator="+", operand=operand)
        assert _infer_expr(node) == ExprResultType.NUMERIC

    def test_unary_minus(self):
        operand = MLiteral(value=123, literal_type=LiteralType.INTEGER)
        node = MUnaryOp(operator="-", operand=operand)
        assert _infer_expr(node) == ExprResultType.NUMERIC


@pytest.mark.codegen
class TestInferExprPatternMatch:
    """Test type inference for pattern matching."""

    def test_pattern_match(self):
        subject = MLiteral(value="test", literal_type=LiteralType.STRING)
        node = MPatternMatch(subject=subject, pattern=[], pattern_indirect=None)
        assert _infer_expr(node) == ExprResultType.BOOLEAN_INT


@pytest.mark.codegen
class TestInferExprIntrinsicFunctions:
    """Test type inference for intrinsic functions."""

    def test_numeric_functions(self):
        """$LENGTH, $ASCII, $FIND, $RANDOM, $DATA, etc. return NUMERIC."""
        for name in [
            "LENGTH",
            "ASCII",
            "FIND",
            "RANDOM",
            "DATA",
            "L",
            "A",
            "F",
            "R",
            "D",
        ]:
            node = MIntrinsicFunction(name=name, arguments=[])
            assert _infer_expr(node) == ExprResultType.NUMERIC, f"Failed for ${name}"

    def test_string_functions(self):
        """$PIECE, $EXTRACT, $CHAR, $TRANSLATE, etc. return STRING."""
        for name in ["PIECE", "EXTRACT", "CHAR", "TRANSLATE", "REVERSE", "P", "E", "C"]:
            node = MIntrinsicFunction(name=name, arguments=[])
            assert _infer_expr(node) == ExprResultType.STRING, f"Failed for ${name}"

    def test_numeric_string_functions(self):
        """$JUSTIFY, $FNUMBER return NUMERIC_STRING."""
        for name in ["JUSTIFY", "FNUMBER", "J", "FN"]:
            node = MIntrinsicFunction(name=name, arguments=[])
            assert _infer_expr(node) == ExprResultType.NUMERIC_STRING, (
                f"Failed for ${name}"
            )

    def test_unknown_functions(self):
        """$GET, $SELECT, $ORDER return UNKNOWN (polymorphic)."""
        for name in ["GET", "SELECT", "ORDER", "G", "S", "O"]:
            node = MIntrinsicFunction(name=name, arguments=[])
            assert _infer_expr(node) == ExprResultType.UNKNOWN, f"Failed for ${name}"

    def test_stack_function_single_arg(self):
        """$STACK with 1 arg returns NUMERIC."""
        arg = MLiteral(value=1, literal_type=LiteralType.INTEGER)
        node = MIntrinsicFunction(name="STACK", arguments=[arg])
        assert _infer_expr(node) == ExprResultType.NUMERIC

    def test_stack_function_two_args(self):
        """$STACK with 2 args returns STRING."""
        arg1 = MLiteral(value=1, literal_type=LiteralType.INTEGER)
        arg2 = MLiteral(value="PLACE", literal_type=LiteralType.STRING)
        node = MIntrinsicFunction(name="STACK", arguments=[arg1, arg2])
        assert _infer_expr(node) == ExprResultType.STRING


@pytest.mark.codegen
class TestInferExprSpecialVariables:
    """Test type inference for special variables."""

    def test_boolean_svars(self):
        """$TEST, $TLEVEL return BOOLEAN_INT."""
        for name in ["TEST", "TLEVEL", "T", "TL"]:
            node = MSpecialVariable(name=name)
            assert _infer_expr(node) == ExprResultType.BOOLEAN_INT, (
                f"Failed for ${name}"
            )

    def test_string_svars(self):
        """$HOROLOG, $JOB, $IO, etc. return STRING."""
        for name in ["HOROLOG", "JOB", "IO", "ZSTATUS", "H", "J", "I"]:
            node = MSpecialVariable(name=name)
            assert _infer_expr(node) == ExprResultType.STRING, f"Failed for ${name}"


@pytest.mark.codegen
class TestInferExprOtherExprTypes:
    """Test type inference for other expression types."""

    def test_extrinsic_function(self):
        node = MExtrinsicFunction(target=None, arguments=[])
        assert _infer_expr(node) == ExprResultType.UNKNOWN

    def test_external_function(self):
        node = MExternalFunction(package=None, name="TEST", arguments=[])
        assert _infer_expr(node) == ExprResultType.UNKNOWN

    def test_indirection(self):
        expr = MLiteral(value="X", literal_type=LiteralType.STRING)
        node = MIndirection(
            expression=expr, subscripts=None, name_indirection_subscripts=None
        )
        assert _infer_expr(node) == ExprResultType.UNKNOWN

    def test_structured_system_variable(self):
        node = MStructuredSystemVariable(name="JOB", subscripts=[])
        assert _infer_expr(node) == ExprResultType.UNKNOWN


@pytest.mark.codegen
class TestInferExpressionTypesIntegration:
    """Test the full type inference pass on parsed routines."""

    def test_simple_routine(self):
        """Verify type inference runs without error on a simple routine."""
        code = """\
TEST ; Test routine
 S X=1+2
 S Y="hello"_"world"
 W X>Y,!
 Q
"""
        routine = _parse(code)
        # Should not raise
        infer_expression_types(routine)

    def test_routine_with_functions(self):
        """Verify type inference handles intrinsic functions."""
        code = """\
TEST ; Test routine
 S X=$L("test")
 S Y=$P("a,b,c",",",2)
 Q
"""
        routine = _parse(code)
        infer_expression_types(routine)

    def test_routine_with_for_loop(self):
        """Verify type inference walks FOR statement expressions."""
        code = """\
TEST ; Test routine
 F I=1:1:10 W I,!
 Q
"""
        routine = _parse(code)
        infer_expression_types(routine)

    def test_routine_with_postcondition(self):
        """Verify type inference handles postconditions."""
        code = """\
TEST ; Test routine
 W:X>0 "positive",!
 Q
"""
        routine = _parse(code)
        infer_expression_types(routine)

    def test_empty_routine(self):
        """Empty routine should not raise."""
        code = "TEST\n"
        routine = _parse(code)
        infer_expression_types(routine)

    def test_routine_with_multiple_labels(self):
        """Routine with multiple labels should process all."""
        code = """\
TEST ; Label 1
 S A=1
 Q
LABEL2 ; Label 2
 S B=2+3
 Q
"""
        routine = _parse(code)
        infer_expression_types(routine)

    def test_nested_expressions(self):
        """Deeply nested expressions should be handled correctly."""
        code = """\
TEST ; Nested
 S X=((1+2)*3)+$L("test")
 Q
"""
        routine = _parse(code)
        infer_expression_types(routine)
