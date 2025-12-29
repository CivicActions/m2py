"""Unit tests for the semantic analyzer.

Tests expression analysis and the unwrap_expression function.
Command analysis tests are in test_command_analysis.py.
"""

from tests.helpers.parsing import parse_expression
from m2py.analysis.semantic_analyzer import analyze_expression, unwrap_expression
from m2py.asg.expressions import (
    MLiteral,
    MVariable,
    MGlobal,
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
    """Test MPatternMatch ASG node structure.

    Pattern match expressions parse as MPatternMatch nodes with:
    - subject: the left-hand expression being matched
    - pattern: string representation of the pattern specification
    - operator: either "?" or "'?" for negated match
    """

    def test_pattern_match_as_pattern_match(self):
        """Pattern match X?1N parses as MPatternMatch."""
        from m2py.asg import MPatternMatch

        expr = parse_expression("X?1N")
        result = analyze_expression(expr)

        assert isinstance(result, MPatternMatch)
        assert result.operator == "?"
        assert isinstance(result.subject, MVariable)
        assert result.subject.name == "X"
        assert result.pattern == "1N"

    def test_pattern_match_recognizable(self):
        """Pattern match can be identified by MPatternMatch type."""
        from m2py.asg import MPatternMatch

        expr = parse_expression("Y?1A")
        result = analyze_expression(expr)

        # Can identify pattern match by type
        assert isinstance(result, MPatternMatch)
        assert result.operator == "?"
        assert result.pattern == "1A"

    def test_pattern_match_indefinite_multiplier(self):
        """Indefinite multiplier .N parses correctly (zero or more)."""
        from m2py.asg import MPatternMatch

        expr = parse_expression("X?.N")
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

        expr = parse_expression("X?1.3N")
        result = analyze_expression(expr)

        assert isinstance(result, MPatternMatch)
        assert result.pattern == "1.3N"

    def test_pattern_match_multiple_atoms(self):
        """Multiple pattern atoms like 1N.A parses correctly."""
        from m2py.asg import MPatternMatch

        expr = parse_expression("X?1N.A")
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

        expr = parse_expression("X?.N_Y")
        result = analyze_expression(expr)

        # Result is a binary op (_) with left being pattern match
        assert isinstance(result, MBinaryOp)
        assert result.operator == "_"
        assert isinstance(result.left, MPatternMatch)
        assert result.left.pattern == ".N"


class TestIntrinsicFunctionASG:
    """Test MIntrinsicFunction ASG node structure."""

    def test_piece_function_args(self):
        """$PIECE(str,delim,pos) has 3 arguments."""
        expr = parse_expression('$PIECE(X,":",2)')
        result = analyze_expression(expr)

        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "PIECE"
        assert len(result.arguments) == 3

    def test_length_function_args(self):
        """$LENGTH(str) has 1 argument."""
        expr = parse_expression("$LENGTH(X)")
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

    def test_binary_expression_in_function_arg(self):
        """$T(TEX+I) has a binary expression argument - regression test for T582.

        This tests that binary expressions inside function arguments are correctly
        preserved and not dropped during unwrapping. Previously, _unwrap_expr()
        checked for '.ops' attribute but the grammar uses '.tail' for BinaryOpTail.
        """
        expr = parse_expression("$T(TEX+I)")
        result = analyze_expression(expr)

        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "T"
        assert len(result.arguments) == 1

        # The argument should be an MBinaryOp, not just LocalVariable
        arg = result.arguments[0]
        assert isinstance(arg, MBinaryOp), (
            f"Expected MBinaryOp, got {type(arg).__name__}"
        )
        assert arg.operator == "+"

        # Left should be TEX, right should be I
        assert isinstance(arg.left, MVariable)
        assert arg.left.name == "TEX"
        assert isinstance(arg.right, MVariable)
        assert arg.right.name == "I"

    def test_complex_expression_in_function_arg(self):
        """$P(A," ;",2,99) preserves all arguments including string literals."""
        expr = parse_expression('$P(A," ;",2,99)')
        result = analyze_expression(expr)

        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "P"
        assert len(result.arguments) == 4

        # First arg is variable A
        assert isinstance(result.arguments[0], MVariable)
        assert result.arguments[0].name == "A"

        # Second arg is string literal " ;"
        assert isinstance(result.arguments[1], MLiteral)
        assert result.arguments[1].value == " ;"

        # Third and fourth args are numeric literals
        assert isinstance(result.arguments[2], MLiteral)
        assert result.arguments[2].value == 2
        assert isinstance(result.arguments[3], MLiteral)
        assert result.arguments[3].value == 99


class TestExtrinsicFunctionASG:
    """Test MExtrinsicFunction ASG node structure."""

    def test_extrinsic_simple(self):
        """$$FUNC creates MExtrinsicFunction with target."""
        from m2py.asg import MExtrinsicFunction

        expr = parse_expression("$$MYFUNC")
        result = analyze_expression(expr)

        assert isinstance(result, MExtrinsicFunction)
        assert result.target is not None
        assert result.target.name == "MYFUNC"

    def test_extrinsic_with_routine(self):
        """$$FUNC^ROUTINE has routine reference in target."""
        from m2py.asg import MExtrinsicFunction

        expr = parse_expression("$$CALC^UTILS")
        result = analyze_expression(expr)

        assert isinstance(result, MExtrinsicFunction)
        assert result.target is not None
        assert result.target.name == "CALC"
        assert result.target.routine == "UTILS"

    def test_extrinsic_with_args(self):
        """$$FUNC(a,b) has arguments list."""
        from m2py.asg import MExtrinsicFunction

        expr = parse_expression("$$ADD(1,2)")
        result = analyze_expression(expr)

        assert isinstance(result, MExtrinsicFunction)
        assert len(result.arguments) == 2

    def test_extrinsic_with_byref_args(self):
        """$$FUNC(.X,Y,.Z) preserves by-reference passing mode.

        MUMPS spec 8.1.7: .actualname = call-by-reference format.
        """
        from m2py.asg import MExtrinsicFunction, MActualParameter, PassingMode

        expr = parse_expression("$$CALC(.A,B,.C)")
        result = analyze_expression(expr)

        assert isinstance(result, MExtrinsicFunction)
        assert len(result.arguments) == 3

        # First arg: .A is by-reference
        assert isinstance(result.arguments[0], MActualParameter)
        assert result.arguments[0].passing_mode == PassingMode.BY_REFERENCE
        assert result.arguments[0].variable_name == "A"

        # Second arg: B is by-value
        assert isinstance(result.arguments[1], MActualParameter)
        assert result.arguments[1].passing_mode == PassingMode.BY_VALUE

        # Third arg: .C is by-reference
        assert isinstance(result.arguments[2], MActualParameter)
        assert result.arguments[2].passing_mode == PassingMode.BY_REFERENCE
        assert result.arguments[2].variable_name == "C"


class TestIndirectionASG:
    """Test MIndirection ASG node structure."""

    def test_indirection_simple(self):
        """@X creates MIndirection with expression."""
        from m2py.asg import MIndirection

        expr = parse_expression("@X")
        result = analyze_expression(expr)

        assert isinstance(result, MIndirection)
        assert result.expression is not None
        assert isinstance(result.expression, MVariable)
        assert result.expression.name == "X"

    def test_indirection_subscripted(self):
        """@X(1) creates MIndirection with subscripts."""
        from m2py.asg import MIndirection

        expr = parse_expression("@X(1)")
        result = analyze_expression(expr)

        assert isinstance(result, MIndirection)
        assert result.expression is not None


class TestSpecialVariableASG:
    """Test MSpecialVariable ASG node structure."""

    def test_test_variable(self):
        """$TEST creates MSpecialVariable with name."""
        from m2py.asg import MSpecialVariable

        expr = parse_expression("$TEST")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "TEST"

    def test_horolog_variable(self):
        """$HOROLOG creates MSpecialVariable."""
        from m2py.asg import MSpecialVariable

        expr = parse_expression("$HOROLOG")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "HOROLOG"

    def test_job_variable(self):
        """$JOB creates MSpecialVariable."""
        from m2py.asg import MSpecialVariable

        expr = parse_expression("$JOB")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "JOB"

    def test_abbreviated_horolog(self):
        """$H creates MSpecialVariable with name 'H' (single-letter abbreviation)."""
        from m2py.asg import MSpecialVariable

        expr = parse_expression("$H")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "H"

    def test_abbreviated_storage(self):
        """$S creates MSpecialVariable with name 'S' (single-letter abbreviation)."""
        from m2py.asg import MSpecialVariable

        expr = parse_expression("$S")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "S"

    def test_abbreviated_test(self):
        """$T creates MSpecialVariable with name 'T' (single-letter abbreviation)."""
        from m2py.asg import MSpecialVariable

        expr = parse_expression("$T")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "T"

    def test_abbreviated_job(self):
        """$J creates MSpecialVariable with name 'J' (single-letter abbreviation)."""
        from m2py.asg import MSpecialVariable

        expr = parse_expression("$J")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "J"


class TestFormatControlASG:
    """Test MFormatControl ASG nodes for Write format controls (!, #, ?n)."""

    def test_newline_control(self):
        """W ! produces MFormatControl with NEWLINE type."""
        from m2py.asg import MFormatControl, FormatControlType
        from m2py.asg.statements import MWriteStatement
        from tests.helpers.parsing import parse_command
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
        from tests.helpers.parsing import parse_command
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
        from tests.helpers.parsing import parse_command
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
        from tests.helpers.parsing import parse_command
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
        from tests.helpers.parsing import parse_command
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


class TestXecuteConstantDetection:
    """Tests for XECUTE constant detection (literal string arguments)."""

    def test_xecute_constant_string(self):
        """X "S X=1" should be detected as constant."""
        from m2py.asg.statements import MXecuteStatement
        from tests.helpers.parsing import parse_command
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer

        cmd = parse_command('X "S X=1"')
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(cmd, None)

        assert isinstance(result, MXecuteStatement)
        assert result.is_constant is True
        assert result.constant_values == ["S X=1"]

    def test_xecute_multiple_constants(self):
        """X "S X=1","S Y=2" should detect both as constant."""
        from m2py.asg.statements import MXecuteStatement
        from tests.helpers.parsing import parse_command
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer

        cmd = parse_command('X "S X=1","S Y=2"')
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(cmd, None)

        assert isinstance(result, MXecuteStatement)
        assert result.is_constant is True
        assert result.constant_values == ["S X=1", "S Y=2"]

    def test_xecute_variable_expression(self):
        """X CODE should not be detected as constant."""
        from m2py.asg.statements import MXecuteStatement
        from tests.helpers.parsing import parse_command
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer

        cmd = parse_command("X CODE")
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(cmd, None)

        assert isinstance(result, MXecuteStatement)
        assert result.is_constant is False
        assert result.constant_values == []

    def test_xecute_mixed_args(self):
        """X "S X=1",CODE should not be detected as constant."""
        from m2py.asg.statements import MXecuteStatement
        from tests.helpers.parsing import parse_command
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer

        cmd = parse_command('X "S X=1",CODE')
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(cmd, None)

        assert isinstance(result, MXecuteStatement)
        assert result.is_constant is False


class TestPatternMatchCompilation:
    """Tests for pattern match regex compilation."""

    def test_pattern_match_compiled_regex(self):
        """X?1A.N should have compiled_regex set."""
        from m2py.asg.expressions import MPatternMatch
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression

        expr = parse_expression("X?1A.N")
        result = analyze_expression(expr)

        assert isinstance(result, MPatternMatch)
        assert result.pattern == "1A.N"
        assert result.compiled_regex is not None
        # Verify the regex is valid
        import re

        re.compile(result.compiled_regex)

    def test_pattern_match_alphanumeric(self):
        """X?1A.AN should compile to alphanumeric pattern."""
        from m2py.asg.expressions import MPatternMatch
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        import re

        expr = parse_expression("X?.AN")
        result = analyze_expression(expr)

        assert isinstance(result, MPatternMatch)
        assert result.compiled_regex is not None
        # Verify it matches alphanumeric strings
        assert re.fullmatch(result.compiled_regex, "Test123")
        assert re.fullmatch(result.compiled_regex, "")


class TestIndirectionClassification:
    """Tests for indirection type classification and static resolution."""

    def test_indirection_default_type(self):
        """@X should have IndirectionType.NAME by default."""
        from m2py.asg.expressions import MIndirection
        from m2py.asg.enums import IndirectionType
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression

        expr = parse_expression("@X")
        result = analyze_expression(expr)

        assert isinstance(result, MIndirection)
        assert result.indirection_type == IndirectionType.NAME

    def test_indirection_static_resolution_string(self):
        """@"VARNAME" should resolve statically."""
        from m2py.asg.expressions import MIndirection
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression

        expr = parse_expression('@"VARNAME"')
        result = analyze_expression(expr)

        assert isinstance(result, MIndirection)
        assert result.can_resolve_statically is True
        assert result.resolved_value == "VARNAME"

    def test_indirection_variable_not_static(self):
        """@X should not resolve statically."""
        from m2py.asg.expressions import MIndirection
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression

        expr = parse_expression("@X")
        result = analyze_expression(expr)

        assert isinstance(result, MIndirection)
        assert result.can_resolve_statically is False
        assert result.resolved_value is None


class TestReadFixedLength:
    """Tests for READ command with fixed-length syntax (R X#n)."""

    def test_read_fixed_length_basic(self):
        """R X#5 should produce MReadTarget with fixed_length."""
        from m2py.asg.statements import MReadStatement, MReadTarget
        from m2py.parser.line_parser import parse_commands_from_line
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer

        cmds = parse_commands_from_line("R X#5")
        assert len(cmds) == 1

        analyzer = SemanticAnalyzer()
        stmt = analyzer.analyze(cmds[0], None)

        assert isinstance(stmt, MReadStatement)
        assert len(stmt.arguments) == 1

        read_target = stmt.arguments[0]
        assert isinstance(read_target, MReadTarget)
        assert read_target.variable.name == "X"
        assert read_target.fixed_length is not None
        assert read_target.fixed_length.value == 5
        assert read_target.timeout is None

    def test_read_fixed_length_with_timeout(self):
        """R X#5:10 should have both fixed_length and timeout."""
        from m2py.asg.statements import MReadStatement, MReadTarget
        from m2py.parser.line_parser import parse_commands_from_line
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer

        cmds = parse_commands_from_line("R X#5:10")
        assert len(cmds) == 1

        analyzer = SemanticAnalyzer()
        stmt = analyzer.analyze(cmds[0], None)

        assert isinstance(stmt, MReadStatement)
        assert len(stmt.arguments) == 1

        read_target = stmt.arguments[0]
        assert isinstance(read_target, MReadTarget)
        assert read_target.variable.name == "X"
        assert read_target.fixed_length is not None
        assert read_target.fixed_length.value == 5
        assert read_target.timeout is not None
        assert read_target.timeout.value == 10

    def test_read_fixed_length_negative(self):
        """R X#-1 should parse (runtime error, not parse error)."""
        from m2py.asg.statements import MReadStatement
        from m2py.parser.line_parser import parse_commands_from_line
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer

        cmds = parse_commands_from_line("R X#-1")
        assert len(cmds) == 1

        analyzer = SemanticAnalyzer()
        stmt = analyzer.analyze(cmds[0], None)

        assert isinstance(stmt, MReadStatement)
        assert len(stmt.arguments) == 1

        read_target = stmt.arguments[0]
        assert read_target.fixed_length is not None
        # Negative value captured in expression tree

    def test_read_fixed_length_variable(self):
        """R X#N should have variable as fixed_length."""
        from m2py.asg.statements import MReadStatement, MReadTarget
        from m2py.asg.expressions import MVariable
        from m2py.parser.line_parser import parse_commands_from_line
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer

        cmds = parse_commands_from_line("R X#N")
        assert len(cmds) == 1

        analyzer = SemanticAnalyzer()
        stmt = analyzer.analyze(cmds[0], None)

        assert isinstance(stmt, MReadStatement)
        read_target = stmt.arguments[0]
        assert isinstance(read_target, MReadTarget)
        assert read_target.fixed_length is not None
        # Length is a variable reference
        assert isinstance(read_target.fixed_length, MVariable)
        assert read_target.fixed_length.name == "N"

    def test_kill_followed_by_read_fixed_length(self):
        """K A R A#-1 should parse both KILL and READ correctly."""
        from m2py.asg.statements import MKillStatement, MReadStatement, MReadTarget
        from m2py.parser.line_parser import parse_commands_from_line
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer

        cmds = parse_commands_from_line("K A R A#-1")
        assert len(cmds) == 2

        analyzer = SemanticAnalyzer()
        kill_stmt = analyzer.analyze(cmds[0], None)
        read_stmt = analyzer.analyze(cmds[1], None)

        assert isinstance(kill_stmt, MKillStatement)
        assert isinstance(read_stmt, MReadStatement)

        read_target = read_stmt.arguments[0]
        assert isinstance(read_target, MReadTarget)
        assert read_target.variable.name == "A"
        assert read_target.fixed_length is not None
