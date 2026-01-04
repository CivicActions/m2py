"""Tests for HANG command ASG analysis (§8.2.8).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.8
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MHangStatement, MHaltStatement


@pytest.mark.asg
class TestHangCommandAnalysis:
    """ASG-level tests for HANG command analysis (§8.2.8)."""

    def test_hang_command_node(self, analyze_routine):
        """HANG command creates correct ASG node (§8.2.8)."""
        stmt = analyze_first_command("H 5")
        assert isinstance(stmt, MHangStatement)

    def test_hang_duration_expression(self, analyze_routine):
        """HANG duration expression is analyzed (§8.2.8)."""
        stmt = analyze_first_command("H 5")
        assert isinstance(stmt, MHangStatement)
        assert stmt.duration is not None

    def test_hang_vs_halt_disambiguation(self, analyze_routine):
        """H with argument is HANG, H alone is HALT."""
        halt_stmt = analyze_first_command("H")
        hang_stmt = analyze_first_command("H 5")

        assert isinstance(halt_stmt, MHaltStatement)
        assert isinstance(hang_stmt, MHangStatement)
        assert hang_stmt.duration is not None


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])
