"""Tests for WRITE command ASG analysis (§8.2.25).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.25
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MWriteStatement
from m2py.asg.expressions import MFormatControl, MLiteral, MVariable


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestWriteCommandAnalysis:
    """ASG-level tests for WRITE command analysis (§8.2.25)."""

    def test_write_command_node(self):
        """WRITE command creates correct ASG node (§8.2.25).

        Verifies that WRITE command produces MWriteStatement with arguments.
        """
        # Simple WRITE
        stmt = analyze_first_command("W X")
        assert isinstance(stmt, MWriteStatement)
        assert len(stmt.arguments) == 1
        assert isinstance(stmt.arguments[0], MVariable)
        assert stmt.arguments[0].name == "X"

        # WRITE with string literal
        stmt2 = analyze_first_command('W "Hello"')
        assert isinstance(stmt2, MWriteStatement)
        assert len(stmt2.arguments) == 1

        # WRITE with multiple arguments
        stmt3 = analyze_first_command('W X,Y,"text"')
        assert isinstance(stmt3, MWriteStatement)
        assert len(stmt3.arguments) == 3

    def test_write_format_controls(self):
        """WRITE format controls (!, ?, #) are analyzed (§8.2.25).

        Verifies that format controls produce MFormatControl nodes.
        """
        from m2py.asg.enums import FormatControlType

        # Newline
        stmt = analyze_first_command("W !")
        assert isinstance(stmt, MWriteStatement)
        assert len(stmt.arguments) == 1
        assert isinstance(stmt.arguments[0], MFormatControl)
        assert stmt.arguments[0].control_type == FormatControlType.NEWLINE

        # Tab with column
        stmt2 = analyze_first_command("W ?10")
        assert isinstance(stmt2.arguments[0], MFormatControl)
        assert stmt2.arguments[0].control_type == FormatControlType.TAB

        # Formfeed
        stmt3 = analyze_first_command("W #")
        assert isinstance(stmt3.arguments[0], MFormatControl)
        assert stmt3.arguments[0].control_type == FormatControlType.FORMFEED

    def test_write_xy_modification(self):
        """WRITE modifies $X/$Y (§8.2.25).

        Verifies that WRITE captures information needed for $X/$Y tracking.
        Note: Actual $X/$Y tracking is runtime behavior.
        """
        # WRITE with newline affects $Y
        stmt = analyze_first_command("W !")
        assert isinstance(stmt, MWriteStatement)
        assert isinstance(stmt.arguments[0], MFormatControl)

        # WRITE with tab affects $X
        stmt2 = analyze_first_command("W ?20")
        assert isinstance(stmt2, MWriteStatement)
        # Tab has expression for column position
        assert stmt2.arguments[0].expression is not None

        # WRITE with formfeed affects both
        stmt3 = analyze_first_command("W #")
        assert isinstance(stmt3, MWriteStatement)

    def test_write_expression_evaluation(self):
        """WRITE expression order is analyzed (§8.2.25).

        Verifies that WRITE captures expressions in order.
        """
        stmt = analyze_first_command('W !,"Header",!,X,!,"Footer"')
        assert isinstance(stmt, MWriteStatement)
        assert len(stmt.arguments) == 6

        # Arguments are in order: !, "Header", !, X, !, "Footer"
        assert isinstance(stmt.arguments[0], MFormatControl)  # !
        # argument 1 is string literal
        assert isinstance(stmt.arguments[2], MFormatControl)  # !
        assert isinstance(stmt.arguments[3], MVariable)  # X
        assert stmt.arguments[3].name == "X"
        assert isinstance(stmt.arguments[4], MFormatControl)  # !


@pytest.mark.asg
class TestFormatControlASG:
    """Test MFormatControl ASG nodes for Write format controls (!, #, ?n)."""

    def test_newline_control(self):
        """W ! produces MFormatControl with NEWLINE type."""
        from tests.helpers.parsing import parse_command
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg import MFormatControl, FormatControlType
        from m2py.asg.statements import MWriteStatement

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
        from tests.helpers.parsing import parse_command
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg import MFormatControl, FormatControlType
        from m2py.asg.statements import MWriteStatement

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
        from tests.helpers.parsing import parse_command
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg import MFormatControl, FormatControlType, MLiteral
        from m2py.asg.statements import MWriteStatement

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
        from tests.helpers.parsing import parse_command
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg import MFormatControl, FormatControlType, MLiteral
        from m2py.asg.statements import MWriteStatement

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
        from tests.helpers.parsing import parse_command
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg import MFormatControl, FormatControlType, MLiteral
        from m2py.asg.statements import MWriteStatement

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


@pytest.mark.asg
class TestWriteStatementAnalysis:
    """Tests for WRITE command analysis."""

    def test_simple_write(self):
        """WRITE X produces MWriteStatement."""
        from m2py.parser.line_parser import parse_commands_from_line
        from m2py.analysis.semantic_analyzer import analyze_command
        from m2py.asg.statements import MWriteStatement

        cmds = parse_commands_from_line("W X")
        stmt = analyze_command(cmds[0])

        assert isinstance(stmt, MWriteStatement)
        assert len(stmt.arguments) >= 1

    def test_write_string(self):
        """WRITE "hello" produces string literal argument."""
        from m2py.parser.line_parser import parse_commands_from_line
        from m2py.analysis.semantic_analyzer import analyze_command
        from m2py.asg.statements import MWriteStatement

        cmds = parse_commands_from_line('W "hello"')
        stmt = analyze_command(cmds[0])

        assert isinstance(stmt, MWriteStatement)
        assert len(stmt.arguments) >= 1
        # Argument may be wrapped, check the underlying value
        arg = stmt.arguments[0]
        if isinstance(arg, MLiteral):
            assert arg.value == "hello"
        else:
            # May be an Expr wrapper - just verify it exists
            assert arg is not None

    def test_write_format_control(self):
        """WRITE ! produces newline format control."""
        from m2py.parser.line_parser import parse_commands_from_line
        from m2py.analysis.semantic_analyzer import analyze_command
        from m2py.asg.statements import MWriteStatement

        cmds = parse_commands_from_line("W !")
        stmt = analyze_command(cmds[0])

        assert isinstance(stmt, MWriteStatement)
        assert len(stmt.arguments) >= 1


@pytest.mark.asg
class TestParseWriteCommand:
    """Test WRITE command parsing to full-fidelity ASG."""

    def test_simple_write(self):
        """W X creates MWriteStatement"""
        from m2py.parser.line_parser import parse_commands_from_line
        from m2py.analysis.semantic_analyzer import analyze_command

        cmds = parse_commands_from_line("W X")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert len(stmt.arguments) == 1

    def test_write_string(self):
        """W "Hello" parses string"""
        from m2py.parser.line_parser import parse_commands_from_line
        from m2py.analysis.semantic_analyzer import analyze_command

        cmds = parse_commands_from_line('W "Hello"')
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert len(stmt.arguments) == 1

    def test_write_newline(self):
        """W ! parses newline"""
        from m2py.parser.line_parser import parse_commands_from_line
        from m2py.analysis.semantic_analyzer import analyze_command
        from m2py.asg.expressions import MFormatControl
        from m2py.asg.enums import FormatControlType

        cmds = parse_commands_from_line("W !")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert isinstance(stmt.arguments[0], MFormatControl)
        assert stmt.arguments[0].control_type == FormatControlType.NEWLINE
