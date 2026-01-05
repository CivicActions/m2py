"""Tests for XECUTE command ASG analysis (§8.2.26).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.26
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MXecuteStatement


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestXecuteCommandAnalysis:
    """ASG-level tests for XECUTE command analysis (§8.2.26)."""

    def test_xecute_command_node(self):
        """XECUTE command creates correct ASG node (§8.2.26).

        Verifies that XECUTE command produces MXecuteStatement.
        """
        # Simple XECUTE with literal
        stmt = analyze_first_command('X "S X=1"')
        assert isinstance(stmt, MXecuteStatement)

        # XECUTE with variable
        stmt2 = analyze_first_command("X CODE")
        assert isinstance(stmt2, MXecuteStatement)

        # XECUTE with multiple expressions
        stmt3 = analyze_first_command('X "S X=1","S Y=2"')
        assert isinstance(stmt3, MXecuteStatement)

    def test_xecute_static_analysis_limitation(self):
        """XECUTE limits static analysis (§8.2.26).

        Verifies that XECUTE captures is_constant flag to indicate
        whether static analysis is possible.
        """
        # Constant XECUTE - can be statically analyzed
        stmt = analyze_first_command('X "S X=1"')
        assert isinstance(stmt, MXecuteStatement)
        assert stmt.is_constant is True
        assert stmt.constant_values == ["S X=1"]

        # Variable XECUTE - cannot be statically analyzed
        stmt2 = analyze_first_command("X CODE")
        assert isinstance(stmt2, MXecuteStatement)
        assert stmt2.is_constant is False
        assert stmt2.constant_values == []

    def test_xecute_postcondition(self):
        """XECUTE expr:condition is analyzed (§8.2.26).

        Verifies that XECUTE captures postcondition on command.
        """
        # XECUTE with command postcondition
        stmt = analyze_first_command('X:flag "S X=1"')
        assert isinstance(stmt, MXecuteStatement)
        # Command-level postcondition
        assert stmt.postcondition is not None


@pytest.mark.asg
class TestXecuteConstantDetection:
    """Tests for XECUTE constant detection (literal string arguments)."""

    def test_xecute_constant_string(self):
        """X "S X=1" should be detected as constant."""
        from tests.helpers.parsing import parse_command
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.statements import MXecuteStatement

        cmd = parse_command('X "S X=1"')
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(cmd, None)

        assert isinstance(result, MXecuteStatement)
        assert result.is_constant is True
        assert result.constant_values == ["S X=1"]

    def test_xecute_multiple_constants(self):
        """X "S X=1","S Y=2" should detect both as constant."""
        from tests.helpers.parsing import parse_command
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.statements import MXecuteStatement

        cmd = parse_command('X "S X=1","S Y=2"')
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(cmd, None)

        assert isinstance(result, MXecuteStatement)
        assert result.is_constant is True
        assert result.constant_values == ["S X=1", "S Y=2"]

    def test_xecute_variable_expression(self):
        """X CODE should not be detected as constant."""
        from tests.helpers.parsing import parse_command
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.statements import MXecuteStatement

        cmd = parse_command("X CODE")
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(cmd, None)

        assert isinstance(result, MXecuteStatement)
        assert result.is_constant is False
        assert result.constant_values == []

    def test_xecute_mixed_args(self):
        """X "S X=1",CODE should not be detected as constant."""
        from tests.helpers.parsing import parse_command
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.statements import MXecuteStatement

        cmd = parse_command('X "S X=1",CODE')
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(cmd, None)

        assert isinstance(result, MXecuteStatement)
        assert result.is_constant is False
