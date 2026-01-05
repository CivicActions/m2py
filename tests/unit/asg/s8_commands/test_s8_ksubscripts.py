"""Tests for KSUBSCRIPTS command ASG analysis (§8.2.20).

KSUBSCRIPTS is an ANSI 1995 command that kills only the subscripts (descendants)
of a variable, preserving its value:
- KS X deletes X(a), X(a,b), etc. but preserves X's value
- $DATA(X) becomes 0 or 1 (from 10 or 11)

Reference: MUMPS 1995 ANSI Standard, Section 8.2.20
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MKSubscriptsStatement


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestKSubscriptsAnalysis:
    """ASG-level tests for KSUBSCRIPTS (§8.2.20).

    KSUBSCRIPTS is a variant of KILL that:
    - KS glvn: Kills descendants only, preserves value
    - KS (A,B): Exclusive kill of descendants except listed names
    - KS (no args): Kill all local variable descendants
    """

    def test_ksubscripts_asg_node(self):
        """KSUBSCRIPTS produces correct ASG node (§8.2.20).

        Verifies that KSUBSCRIPTS produces MKSubscriptsStatement.
        """
        # Simple KSUBSCRIPTS
        stmt = analyze_first_command("KS X")
        assert isinstance(stmt, MKSubscriptsStatement)
        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "X"
        assert stmt.exclusive is False

        # Full spelling
        stmt2 = analyze_first_command("KSUBSCRIPTS Y")
        assert isinstance(stmt2, MKSubscriptsStatement)
        assert stmt2.targets[0].name == "Y"

        # No arguments (kill all subscripts)
        stmt3 = analyze_first_command("KS")
        assert isinstance(stmt3, MKSubscriptsStatement)
        assert stmt3.is_kill_all is True

    def test_ksubscripts_subscript_analysis(self):
        """KSUBSCRIPTS subscripts are analyzed correctly (§8.2.20).

        Verifies exclusive and selective forms work.
        """
        # Exclusive form
        stmt = analyze_first_command("KS (A,B)")
        assert isinstance(stmt, MKSubscriptsStatement)
        assert stmt.exclusive is True
        assert "A" in stmt.except_list
        assert "B" in stmt.except_list

        # Multiple targets
        stmt2 = analyze_first_command("KS X,Y,Z")
        assert isinstance(stmt2, MKSubscriptsStatement)
        assert len(stmt2.targets) == 3

        # Subscripted target
        stmt3 = analyze_first_command("KS X(1,2)")
        assert isinstance(stmt3, MKSubscriptsStatement)
        assert len(stmt3.targets) == 1
        assert len(stmt3.targets[0].subscripts) == 2
