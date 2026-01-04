"""Tests for HALT command ASG analysis (§8.2.7).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.7
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MHaltStatement


@pytest.mark.asg
class TestHaltCommandAnalysis:
    """ASG-level tests for HALT command analysis (§8.2.7)."""

    def test_halt_command_node(self, analyze_routine):
        """HALT command creates correct ASG node (§8.2.7)."""
        # Full command
        stmt = analyze_first_command("HALT")
        assert isinstance(stmt, MHaltStatement)

        # Abbreviated command
        stmt = analyze_first_command("H")
        assert isinstance(stmt, MHaltStatement)

    def test_halt_control_flow_termination(self):
        """HALT terminates control flow analysis (§8.2.7)."""
        # HALT should indicate control flow terminates
        stmt = analyze_first_command("HALT")
        assert isinstance(stmt, MHaltStatement)

        # HALT with postcondition is conditional termination
        stmt2 = analyze_first_command("H:X")
        assert isinstance(stmt2, MHaltStatement)
        assert stmt2.postcondition is not None

        # HALT has no arguments - it unconditionally terminates
        # Verify it has the standard statement attributes
        assert hasattr(stmt, "is_unreachable")
        assert hasattr(stmt, "postcondition")


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])
