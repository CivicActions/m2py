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
    
    Pattern match expressions now parse as MPatternMatch nodes with:
    - subject: the left-hand expression being matched
    - pattern: string representation of the pattern specification
    - operator: either "?" or "'?" for negated match
    """
    
    def test_pattern_match_as_pattern_match(self):
        """Pattern match X?1N parses as MPatternMatch."""
        from m2py.asg import MPatternMatch
        
        expr = parse_expression('X?1N')
        result = analyze_expression(expr)
        
        assert isinstance(result, MPatternMatch)
        assert result.operator == "?"
        assert isinstance(result.subject, MVariable)
        assert result.subject.name == "X"
        assert result.pattern == "1N"
    
    def test_pattern_match_recognizable(self):
        """Pattern match can be identified by MPatternMatch type."""
        from m2py.asg import MPatternMatch
        
        expr = parse_expression('Y?1A')
        result = analyze_expression(expr)
        
        # Can identify pattern match by type
        assert isinstance(result, MPatternMatch)
        assert result.operator == "?"
        assert result.pattern == "1A"
    
    def test_pattern_match_indefinite_multiplier(self):
        """Indefinite multiplier .N parses correctly (T527)."""
        from m2py.asg import MPatternMatch
        
        expr = parse_expression('X?.N')
        result = analyze_expression(expr)
        
        assert isinstance(result, MPatternMatch)
        assert result.operator == "?"
        assert result.pattern == ".N"
    
    def test_pattern_match_negated(self):
        """Negated pattern match X'?1A parses correctly."""
        from m2py.asg import MPatternMatch
        
        expr = parse_expression("X'?1A")
        result = analyze_expression(expr)
        
        assert isinstance(result, MPatternMatch)
        assert result.operator == "'?"
        assert result.pattern == "1A"
    
    def test_pattern_match_range_repcount(self):
        """Range repcount like 1.3N parses correctly."""
        from m2py.asg import MPatternMatch
        
        expr = parse_expression('X?1.3N')
        result = analyze_expression(expr)
        
        assert isinstance(result, MPatternMatch)
        assert result.pattern == "1.3N"
    
    def test_pattern_match_multiple_atoms(self):
        """Multiple pattern atoms like 1N.A parses correctly."""
        from m2py.asg import MPatternMatch
        
        expr = parse_expression('X?1N.A')
        result = analyze_expression(expr)
        
        assert isinstance(result, MPatternMatch)
        assert result.pattern == "1N.A"
    
    def test_pattern_match_with_string(self):
        """Pattern with string literal like 1"hello" parses correctly."""
        from m2py.asg import MPatternMatch
        
        expr = parse_expression('X?1"hello"')
        result = analyze_expression(expr)
        
        assert isinstance(result, MPatternMatch)
        assert result.pattern == '1"hello"'
    
    def test_pattern_match_followed_by_concat(self):
        """Pattern match followed by concatenation X?.N_Y parses correctly."""
        from m2py.asg import MPatternMatch, MBinaryOp
        
        expr = parse_expression('X?.N_Y')
        result = analyze_expression(expr)
        
        # Result is a binary op (_) with left being pattern match
        assert isinstance(result, MBinaryOp)
        assert result.operator == "_"
        assert isinstance(result.left, MPatternMatch)
        assert result.left.pattern == ".N"


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

class TestFormatControlASG:
    """Test MFormatControl ASG nodes for Write format controls (T524)."""
    
    def test_newline_control(self):
        """W ! produces MFormatControl with NEWLINE type."""
        from m2py.asg import MFormatControl, FormatControlType
        from m2py.asg.statements import MWriteStatement
        from m2py.analysis.command_parser import parse_command
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        
        cmd = parse_command("W !")
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(cmd, None)
        
        assert isinstance(result, MWriteStatement)
        assert len(result.arguments) == 1
        arg = result.arguments[0]
        assert isinstance(arg, MFormatControl)
        assert arg.control_type == FormatControlType.NEWLINE
        assert arg.expression is None
    
    def test_formfeed_control(self):
        """W # produces MFormatControl with FORMFEED type."""
        from m2py.asg import MFormatControl, FormatControlType
        from m2py.asg.statements import MWriteStatement
        from m2py.analysis.command_parser import parse_command
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        
        cmd = parse_command("W #")
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(cmd, None)
        
        assert isinstance(result, MWriteStatement)
        assert len(result.arguments) == 1
        arg = result.arguments[0]
        assert isinstance(arg, MFormatControl)
        assert arg.control_type == FormatControlType.FORMFEED
        assert arg.expression is None
    
    def test_tab_control_with_expression(self):
        """W ?10 produces MFormatControl with TAB type and column expression."""
        from m2py.asg import MFormatControl, FormatControlType, MLiteral
        from m2py.asg.statements import MWriteStatement
        from m2py.analysis.command_parser import parse_command
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        
        cmd = parse_command("W ?10")
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(cmd, None)
        
        assert isinstance(result, MWriteStatement)
        assert len(result.arguments) == 1
        arg = result.arguments[0]
        assert isinstance(arg, MFormatControl)
        assert arg.control_type == FormatControlType.TAB
        assert isinstance(arg.expression, MLiteral)
        assert arg.expression.value == 10
    
    def test_charcode_control_with_expression(self):
        """W *65 produces MFormatControl with CHARCODE type and code expression."""
        from m2py.asg import MFormatControl, FormatControlType, MLiteral
        from m2py.asg.statements import MWriteStatement
        from m2py.analysis.command_parser import parse_command
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        
        cmd = parse_command("W *65")
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(cmd, None)
        
        assert isinstance(result, MWriteStatement)
        assert len(result.arguments) == 1
        arg = result.arguments[0]
        assert isinstance(arg, MFormatControl)
        assert arg.control_type == FormatControlType.CHARCODE
        assert isinstance(arg.expression, MLiteral)
        assert arg.expression.value == 65
    
    def test_mixed_format_controls(self):
        """W !!,"Test",# produces multiple MFormatControl nodes."""
        from m2py.asg import MFormatControl, FormatControlType, MLiteral
        from m2py.asg.statements import MWriteStatement
        from m2py.analysis.command_parser import parse_command
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        
        cmd = parse_command('W !!,"Test",#')
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(cmd, None)
        
        assert isinstance(result, MWriteStatement)
        assert len(result.arguments) == 4
        
        # First two are newlines
        assert isinstance(result.arguments[0], MFormatControl)
        assert result.arguments[0].control_type == FormatControlType.NEWLINE
        assert isinstance(result.arguments[1], MFormatControl)
        assert result.arguments[1].control_type == FormatControlType.NEWLINE
        
        # Third is string literal
        assert isinstance(result.arguments[2], MLiteral)
        assert result.arguments[2].value == "Test"
        
        # Fourth is formfeed
        assert isinstance(result.arguments[3], MFormatControl)
        assert result.arguments[3].control_type == FormatControlType.FORMFEED