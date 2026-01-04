"""Tests for KILL command ASG analysis (§8.2.11).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.11
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
    """ASG-level tests for KILL command analysis (§8.2.11)."""

    def test_kill_simple_target(self):
        """K X produces MKillStatement with single target (§8.2.11)."""
        stmt = analyze_first_command("K X")

        assert isinstance(stmt, MKillStatement)
        assert len(stmt.targets) == 1
        assert stmt.is_kill_all is False

    def test_kill_all_no_arguments(self):
        """K (no args) produces MKillStatement with is_kill_all=True (§8.2.11)."""
        stmt = analyze_first_command("K")

        assert isinstance(stmt, MKillStatement)
        assert len(stmt.targets) == 0
        assert stmt.exclusive is False
        assert stmt.is_kill_all is True

    def test_kill_multiple_targets(self):
        """K X,Y,Z produces MKillStatement with 3 targets (§8.2.11)."""
        stmt = analyze_first_command("K X,Y,Z")

        assert isinstance(stmt, MKillStatement)
        assert len(stmt.targets) == 3
        assert stmt.is_kill_all is False

    def test_kill_exclusive_form(self):
        """K (X,Y) exclusive form is analyzed (§8.2.11)."""
        stmt = analyze_first_command("K (X,Y)")

        assert isinstance(stmt, MKillStatement)
        assert stmt.exclusive is True
        assert stmt.is_kill_all is False

    def test_kill_variable_tracking(self):
        """KILL variable is tracked in output_variables (§8.2.11)."""
        from m2py.asg.expressions import MVariable

        # KILL X marks X as modified (killed)
        stmt = analyze_first_command("K X")
        assert isinstance(stmt, MKillStatement)
        assert len(stmt.targets) == 1
        assert isinstance(stmt.targets[0], MVariable)
        assert stmt.targets[0].name == "X"

        # Multiple targets all tracked
        stmt2 = analyze_first_command("K A,B,C")
        assert isinstance(stmt2, MKillStatement)
        assert len(stmt2.targets) == 3
        target_names = [t.name for t in stmt2.targets]
        assert target_names == ["A", "B", "C"]

        # KILL with exclusive form - tracks preserved variables
        stmt3 = analyze_first_command("K (X,Y)")
        assert isinstance(stmt3, MKillStatement)
        assert stmt3.exclusive is True

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
