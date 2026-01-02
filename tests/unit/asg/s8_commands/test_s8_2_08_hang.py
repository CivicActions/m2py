"""Tests for HANG command ASG analysis (§8.2.8).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.8

Migrated from: tests/unit/test_command_analysis.py::TestOtherStatementAnalysis (partial)
"""

import pytest
from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MHangStatement


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestHangCommandAnalysis:
    """ASG-level tests for HANG command analysis (§8.2.8).

    Migrated from: tests/unit/test_command_analysis.py::TestOtherStatementAnalysis (partial)
    """

    def test_hang(self):
        """H 5 produces MHangStatement (§8.2.8).

        Migrated from: test_command_analysis.py::TestOtherStatementAnalysis::test_hang
        """
        stmt = analyze_first_command("H 5")

        assert isinstance(stmt, MHangStatement)
        assert stmt.duration is not None
