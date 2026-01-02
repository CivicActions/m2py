"""Tests for HALT command ASG analysis (§8.2.7).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.7

Migrated from: tests/unit/test_command_analysis.py::TestOtherStatementAnalysis (partial)
"""

import pytest
from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MHaltStatement, MHangStatement


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestHaltCommandAnalysis:
    """ASG-level tests for HALT command analysis (§8.2.7).

    Migrated from: tests/unit/test_command_analysis.py::TestOtherStatementAnalysis (partial)
    """

    def test_halt(self):
        """HALT produces MHaltStatement (§8.2.7).

        Migrated from: test_command_analysis.py::TestOtherStatementAnalysis::test_halt
        """
        stmt = analyze_first_command("HALT")

        assert isinstance(stmt, MHaltStatement)

    def test_halt_abbreviation(self):
        """H alone (no argument) produces MHaltStatement, not MHangStatement (§8.2.7).

        Per MUMPS spec, H and HALT are the same command when no argument follows.
        H followed by an expression is HANG.

        Migrated from: test_command_analysis.py::TestOtherStatementAnalysis::test_halt_abbreviation
        """
        stmt = analyze_first_command("H")

        assert isinstance(stmt, MHaltStatement)

    def test_hang_vs_halt_disambiguation(self):
        """H with argument is HANG, H alone is HALT (§8.2.7).

        This tests the grammar's correct disambiguation between:
        - H (no argument) → HALT
        - H 5 (with argument) → HANG with duration 5

        Migrated from: test_command_analysis.py::TestOtherStatementAnalysis::test_hang_vs_halt_disambiguation
        """
        halt_stmt = analyze_first_command("H")
        hang_stmt = analyze_first_command("H 5")

        assert isinstance(halt_stmt, MHaltStatement)
        assert isinstance(hang_stmt, MHangStatement)
        assert hang_stmt.duration is not None

    # ---- Stub tests for unimplemented features ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: HALT control flow termination")
    def test_halt_control_flow_termination(self, analyze_routine):
        """HALT terminates control flow analysis (§8.2.7)."""
        pytest.fail("Stub - implement test")
