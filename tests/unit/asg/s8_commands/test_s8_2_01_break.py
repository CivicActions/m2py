"""Tests for BREAK command ASG analysis (§8.2.1).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.1
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MBreakStatement


@pytest.mark.asg
class TestBreakCommandAnalysis:
    """ASG-level tests for BREAK command analysis (§8.2.1)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: BREAK command node")
    def test_break_command_node(self, analyze_routine):
        """BREAK command creates correct ASG node (§8.2.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: BREAK with postcondition")
    def test_break_with_postcondition(self, analyze_routine):
        """BREAK:condition postcondition is analyzed (§8.2.1)."""
        pytest.fail("Stub - implement test")


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestBreakStatementAnalysis:
    """Tests for BREAK statement analysis."""

    def test_break(self):
        """B produces MBreakStatement."""
        stmt = analyze_first_command("B")

        assert isinstance(stmt, MBreakStatement)
