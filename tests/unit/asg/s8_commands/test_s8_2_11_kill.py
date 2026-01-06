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

    def test_kill_global_impact(self):
        """KILL ^GLOBAL impact is tracked (§8.2.11).

        Verifies that KILL with global variable targets produces correct ASG:
        - MGlobal target with correct name and subscripts
        - Multiple global kills tracked separately
        """
        from m2py.asg.expressions import MGlobal, MLiteral

        # Simple global KILL
        stmt = analyze_first_command("K ^GLOBAL")
        assert isinstance(stmt, MKillStatement)
        assert len(stmt.targets) == 1
        target = stmt.targets[0]
        assert isinstance(target, MGlobal)
        assert target.name == "GLOBAL"

        # Global KILL with subscripts
        stmt2 = analyze_first_command("K ^DATA(1,2)")
        assert isinstance(stmt2, MKillStatement)
        assert len(stmt2.targets) == 1
        target2 = stmt2.targets[0]
        assert isinstance(target2, MGlobal)
        assert target2.name == "DATA"
        assert len(target2.subscripts) == 2
        assert isinstance(target2.subscripts[0], MLiteral)
        assert target2.subscripts[0].value == 1

        # Multiple globals
        stmt3 = analyze_first_command("K ^A,^B,^C")
        assert isinstance(stmt3, MKillStatement)
        assert len(stmt3.targets) == 3
        for i, name in enumerate(["A", "B", "C"]):
            assert isinstance(stmt3.targets[i], MGlobal)
            assert stmt3.targets[i].name == name

    def test_kill_subscripted(self):
        """KILL arr(sub) subscripted kill is analyzed (§8.2.11).

        Verifies that KILL with subscripted local variables produces correct ASG:
        - MVariable target with correct subscripts
        - Subscripts can be literals or expressions
        """
        from m2py.asg.expressions import MVariable, MLiteral

        # Single subscript
        stmt = analyze_first_command("K arr(1)")
        assert isinstance(stmt, MKillStatement)
        assert len(stmt.targets) == 1
        target = stmt.targets[0]
        assert isinstance(target, MVariable)
        assert target.name == "arr"
        assert len(target.subscripts) == 1
        assert isinstance(target.subscripts[0], MLiteral)
        assert target.subscripts[0].value == 1

        # Multiple subscripts
        stmt2 = analyze_first_command("K data(1,2,3)")
        assert isinstance(stmt2, MKillStatement)
        target2 = stmt2.targets[0]
        assert isinstance(target2, MVariable)
        assert target2.name == "data"
        assert len(target2.subscripts) == 3

        # Variable subscript
        stmt3 = analyze_first_command("K arr(x)")
        target3 = stmt3.targets[0]
        assert isinstance(target3, MVariable)
        assert target3.name == "arr"
        assert len(target3.subscripts) == 1
        assert isinstance(target3.subscripts[0], MVariable)
        assert target3.subscripts[0].name == "x"

    def test_kill_naked_global(self):
        """KILL ^(sub) uses naked global reference (§7.1.2.4).

        Naked references can be used as KILL targets.
        """
        from m2py.asg.expressions import MNakedGlobal

        stmt = analyze_first_command("K ^(1)")

        assert isinstance(stmt, MKillStatement)
        assert len(stmt.targets) == 1
        target = stmt.targets[0]
        assert isinstance(target, MNakedGlobal)
        assert len(target.subscripts) == 1

    def test_kill_multiple_exclusive_groups(self):
        """K (A,B),(C,D) with multiple exclusive groups computes intersection (§8.2.11).

        Per MUMPS semantics, when multiple exclusive groups are given, only variables
        that appear in ALL groups are preserved (intersection). This is a valid but
        rare syntax: K (A,B),(C,D) means "kill all except those in BOTH lists".

        GAP-003f: Coverage gap for lines 1377-1380 in semantic_analyzer.py.
        """
        stmt = analyze_first_command("K (A,B),(B,C)")

        assert isinstance(stmt, MKillStatement)
        assert stmt.exclusive is True
        # Should have two exclusive groups
        assert len(stmt.except_groups) == 2
        assert stmt.except_groups[0] == ["A", "B"]
        assert stmt.except_groups[1] == ["B", "C"]
        # Intersection: only B is in both groups
        assert stmt.except_list == ["B"]

    def test_kill_multiple_exclusive_groups_no_overlap(self):
        """K (A,B),(C,D) with no overlap results in empty except_list (§8.2.11).

        When exclusive groups have no common variables, the intersection is empty,
        which effectively kills all locals (like K with no args).
        """
        stmt = analyze_first_command("K (A,B),(C,D)")

        assert isinstance(stmt, MKillStatement)
        assert stmt.exclusive is True
        assert len(stmt.except_groups) == 2
        # No intersection - empty list
        assert stmt.except_list == []

    def test_kill_exclusive_then_selective(self):
        """K (A,B),Z is mixed exclusive + selective kill (§8.2.11).

        Per ydb-mumps-guide: "K (a,b),^AB(a,b)" - first argument is exclusive,
        second is a selective target. The exclusive kills all except A,B,
        then Z is also killed.
        """
        stmt = analyze_first_command("K (A,B),Z")

        assert isinstance(stmt, MKillStatement)
        assert stmt.exclusive is True
        # One exclusive group
        assert len(stmt.except_groups) == 1
        assert stmt.except_groups[0] == ["A", "B"]
        # Plus one selective target Z
        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "Z"
