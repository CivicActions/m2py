"""Unit tests for the semantic analyzer.

Tests expression analysis and the unwrap_expression function.
Command analysis tests are in test_command_analysis.py.
"""

import pytest
from m2py.analysis.command_parser import parse_expression
from m2py.analysis.semantic_analyzer import (
    analyze_expression, unwrap_expression
)
from m2py.asg.expressions import (
    MExpr, MLiteral, MVariable, MGlobal, MBinaryOp, MUnaryOp,
    MIntrinsicFunction, MSpecialVariable
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


class TestPatternMatchASG:
    """Test MPatternMatch ASG node structure (T324).
    
    Note: Currently pattern match parses as MBinaryOp with '?' operator.
    The MPatternMatch class exists for future enhancement to capture
    the full pattern structure (pattern codes, etc.).
    """
    
    def test_pattern_match_as_binary_op(self):
        """Pattern match X?1N parses as binary operation."""
        from m2py.asg import MBinaryOp
        
        expr = parse_expression('X?1N')
        result = analyze_expression(expr)
        
        assert isinstance(result, MBinaryOp)
        assert result.operator == "?"
        assert isinstance(result.left, MVariable)
        assert result.left.name == "X"
    
    def test_pattern_match_recognizable(self):
        """Pattern match can be identified by ? operator."""
        from m2py.asg import MBinaryOp
        
        expr = parse_expression('Y?1A')
        result = analyze_expression(expr)
        
        # Can identify pattern match by operator
        assert isinstance(result, MBinaryOp)
        assert result.operator == "?"


class TestIntrinsicFunctionASG:
    """Test MIntrinsicFunction ASG node structure (T325)."""
    
    def test_piece_function_args(self):
        """$PIECE(str,delim,pos) has 3 arguments."""
        expr = parse_expression('$PIECE(X,":",2)')
        result = analyze_expression(expr)
        
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "PIECE"
        assert len(result.arguments) == 3
    
    def test_length_function_args(self):
        """$LENGTH(str) has 1 argument."""
        expr = parse_expression('$LENGTH(X)')
        result = analyze_expression(expr)
        
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "LENGTH"
        assert len(result.arguments) == 1
    
    def test_nested_function_args(self):
        """Nested function $L($P(X,",",1)) has nested arguments."""
        expr = parse_expression('$L($P(X,",",1))')
        result = analyze_expression(expr)
        
        assert isinstance(result, MIntrinsicFunction)
        assert result.name in ("L", "LENGTH")
        assert len(result.arguments) == 1
        
        inner = result.arguments[0]
        assert isinstance(inner, MIntrinsicFunction)
        assert inner.name in ("P", "PIECE")


class TestExtrinsicFunctionASG:
    """Test MExtrinsicFunction ASG node structure (T326)."""
    
    def test_extrinsic_simple(self):
        """$$FUNC creates MExtrinsicFunction with target."""
        from m2py.asg import MExtrinsicFunction
        
        expr = parse_expression('$$MYFUNC')
        result = analyze_expression(expr)
        
        assert isinstance(result, MExtrinsicFunction)
        assert result.target is not None
        assert result.target.name == "MYFUNC"
    
    def test_extrinsic_with_routine(self):
        """$$FUNC^ROUTINE has routine reference in target."""
        from m2py.asg import MExtrinsicFunction
        
        expr = parse_expression('$$CALC^UTILS')
        result = analyze_expression(expr)
        
        assert isinstance(result, MExtrinsicFunction)
        assert result.target is not None
        assert result.target.name == "CALC"
        assert result.target.routine == "UTILS"
    
    def test_extrinsic_with_args(self):
        """$$FUNC(a,b) has arguments list."""
        from m2py.asg import MExtrinsicFunction
        
        expr = parse_expression('$$ADD(1,2)')
        result = analyze_expression(expr)
        
        assert isinstance(result, MExtrinsicFunction)
        assert len(result.arguments) == 2


class TestIndirectionASG:
    """Test MIndirection ASG node structure (T327)."""
    
    def test_indirection_simple(self):
        """@X creates MIndirection with expression."""
        from m2py.asg import MIndirection
        
        expr = parse_expression('@X')
        result = analyze_expression(expr)
        
        assert isinstance(result, MIndirection)
        assert result.expression is not None
        assert isinstance(result.expression, MVariable)
        assert result.expression.name == "X"
    
    def test_indirection_subscripted(self):
        """@X(1) creates MIndirection with subscripts."""
        from m2py.asg import MIndirection
        
        expr = parse_expression('@X(1)')
        result = analyze_expression(expr)
        
        assert isinstance(result, MIndirection)
        assert result.expression is not None


class TestSpecialVariableASG:
    """Test MSpecialVariable ASG node structure (T328)."""
    
    def test_test_variable(self):
        """$TEST creates MSpecialVariable with name."""
        from m2py.asg import MSpecialVariable
        
        expr = parse_expression('$TEST')
        result = analyze_expression(expr)
        
        assert isinstance(result, MSpecialVariable)
        assert result.name == "TEST"
    
    def test_horolog_variable(self):
        """$HOROLOG creates MSpecialVariable."""
        from m2py.asg import MSpecialVariable
        
        expr = parse_expression('$HOROLOG')
        result = analyze_expression(expr)
        
        assert isinstance(result, MSpecialVariable)
        assert result.name == "HOROLOG"
    
    def test_job_variable(self):
        """$JOB creates MSpecialVariable."""
        from m2py.asg import MSpecialVariable
        
        expr = parse_expression('$JOB')
        result = analyze_expression(expr)
        
        assert isinstance(result, MSpecialVariable)
        assert result.name == "JOB"
