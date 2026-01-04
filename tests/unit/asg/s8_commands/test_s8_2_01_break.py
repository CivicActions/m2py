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

    def test_break_command_node(self, analyze_routine):
        """BREAK command creates correct ASG node (§8.2.1)."""
        stmt = analyze_first_command("B")
        assert isinstance(stmt, MBreakStatement)

    def test_break_with_postcondition(self):
        """BREAK:condition postcondition is analyzed (§8.2.1)."""
        # BREAK with postcondition
        stmt = analyze_first_command("B:X")
        assert isinstance(stmt, MBreakStatement)
        assert stmt.postcondition is not None

        # Postcondition should be a variable reference
        from m2py.asg.expressions import MVariable

        assert isinstance(stmt.postcondition, MVariable)
        assert stmt.postcondition.name == "X"

        # BREAK with expression postcondition
        stmt = analyze_first_command("B:X>1")
        assert isinstance(stmt, MBreakStatement)
        assert stmt.postcondition is not None

        from m2py.asg.expressions import MBinaryOp

        assert isinstance(stmt.postcondition, MBinaryOp)
        assert stmt.postcondition.operator == ">"


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])
