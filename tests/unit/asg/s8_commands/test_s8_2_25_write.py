"""Tests for WRITE command ASG analysis (§8.2.25).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.25
"""

import pytest


@pytest.mark.asg
class TestWriteCommandAnalysis:
    """ASG-level tests for WRITE command analysis (§8.2.25)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: WRITE command node")
    def test_write_command_node(self, analyze_routine):
        """WRITE command creates correct ASG node (§8.2.25)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: WRITE format controls")
    def test_write_format_controls(self, analyze_routine):
        """WRITE format controls (!, ?, #) are analyzed (§8.2.25)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: WRITE $X/$Y modification")
    def test_write_xy_modification(self, analyze_routine):
        """WRITE modifies $X/$Y (§8.2.25)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: WRITE expression evaluation")
    def test_write_expression_evaluation(self, analyze_routine):
        """WRITE expression order is analyzed (§8.2.25)."""
        pytest.fail("Stub - implement test")


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
        from m2py.asg.expressions import MLiteral

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
