"""Tests for BREAK command ASG analysis (§8.2.1).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.1

Migrated from: tests/unit/test_command_analysis.py::TestOtherStatementAnalysis (partial)
"""

import pytest
from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MBreakStatement


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestBreakCommandAnalysis:
    """ASG-level tests for BREAK command analysis (§8.2.1).

    Migrated from: tests/unit/test_command_analysis.py::TestOtherStatementAnalysis (partial)
    """

    def test_break(self):
        """B produces MBreakStatement (§8.2.1).

        Migrated from: test_command_analysis.py::TestOtherStatementAnalysis::test_break
        """
        stmt = analyze_first_command("B")

        assert isinstance(stmt, MBreakStatement)

    # ---- Stub tests for unimplemented features ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: BREAK with postcondition")
    def test_break_with_postcondition(self, analyze_routine):
        """BREAK:condition postcondition is analyzed (§8.2.1)."""
        pytest.fail("Stub - implement test")
