"""Tests for KILL command ASG analysis (§8.2.11).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.11

Migrated from: tests/unit/test_command_analysis.py::TestKillStatementAnalysis
"""

import pytest
from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MKillStatement


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestKillCommandAnalysis:
    """ASG-level tests for KILL command analysis (§8.2.11).

    Migrated from: tests/unit/test_command_analysis.py::TestKillStatementAnalysis
    """

    def test_simple_kill(self):
        """K X produces MKillStatement (§8.2.11).

        Migrated from: test_command_analysis.py::TestKillStatementAnalysis::test_simple_kill
        """
        stmt = analyze_first_command("K X")

        assert isinstance(stmt, MKillStatement)
        assert len(stmt.targets) == 1
        assert stmt.is_kill_all is False

    def test_kill_all_no_args(self):
        """K (no args) produces MKillStatement with is_kill_all=True (§8.2.11).

        Migrated from: test_command_analysis.py::TestKillStatementAnalysis::test_kill_all_no_args
        """
        stmt = analyze_first_command("K")

        assert isinstance(stmt, MKillStatement)
        assert len(stmt.targets) == 0
        assert stmt.exclusive is False
        assert stmt.is_kill_all is True

    def test_kill_multiple_targets(self):
        """K X,Y,Z produces MKillStatement with 3 targets (§8.2.11).

        Migrated from: test_command_analysis.py::TestKillStatementAnalysis::test_kill_multiple_targets
        """
        stmt = analyze_first_command("K X,Y,Z")

        assert isinstance(stmt, MKillStatement)
        assert len(stmt.targets) == 3
        assert stmt.is_kill_all is False

    def test_kill_exclusive_not_kill_all(self):
        """K (X,Y) - exclusive kill is NOT kill-all (§8.2.11).

        Migrated from: test_command_analysis.py::TestKillStatementAnalysis::test_kill_exclusive_not_kill_all
        """
        stmt = analyze_first_command("K (X,Y)")

        assert isinstance(stmt, MKillStatement)
        assert stmt.exclusive is True
        assert stmt.is_kill_all is False

    # ---- Stub tests for unimplemented features ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KILL variable tracking")
    def test_kill_variable_tracking(self, analyze_routine):
        """KILL variable is tracked in output_variables (§8.2.11)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KILL global impact")
    def test_kill_global_impact(self, analyze_routine):
        """KILL ^GLOBAL impact is tracked (§8.2.11)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KILL subscripted")
    def test_kill_subscripted(self, analyze_routine):
        """KILL arr(sub) subscripted kill is analyzed (§8.2.11)."""
        pytest.fail("Stub - implement test")
