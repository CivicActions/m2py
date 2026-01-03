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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: HALT command node")
    def test_halt_command_node(self, analyze_routine):
        """HALT command creates correct ASG node (§8.2.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: HALT control flow termination")
    def test_halt_control_flow_termination(self, analyze_routine):
        """HALT terminates control flow analysis (§8.2.7)."""
        pytest.fail("Stub - implement test")


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestHaltStatementAnalysis:
    """Tests for HALT statement analysis."""

    def test_halt(self):
        """HALT produces MHaltStatement."""
        stmt = analyze_first_command("HALT")

        assert isinstance(stmt, MHaltStatement)

    def test_halt_abbreviation(self):
        """H alone (no argument) produces MHaltStatement, not MHangStatement.

        Per MUMPS spec, H and HALT are the same command when no argument follows.
        H followed by an expression is HANG.
        """
        stmt = analyze_first_command("H")

        assert isinstance(stmt, MHaltStatement)
