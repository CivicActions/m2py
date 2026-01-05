"""Tests for KVALUE command ASG analysis (§8.2.21).

KVALUE is an ANSI 1995 command that kills only the value of a variable,
preserving its subscripts (descendants):
- KV X deletes X's value but preserves X(a), X(a,b), etc.
- $DATA(X) becomes 0 or 10 (from 1 or 11)

Reference: MUMPS 1995 ANSI Standard, Section 8.2.21
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MKValueStatement


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestKValueAnalysis:
    """ASG-level tests for KVALUE (§8.2.21).

    KVALUE is a variant of KILL that:
    - KV glvn: Kills value only, preserves descendants
    - KV (A,B): Exclusive kill of values except listed names
    - KV (no args): Kill all local variable values
    """

    def test_kvalue_asg_node(self):
        """KVALUE produces correct ASG node (§8.2.21).

        Verifies that KVALUE produces MKValueStatement.
        """
        # Simple KVALUE
        stmt = analyze_first_command("KV X")
        assert isinstance(stmt, MKValueStatement)
        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "X"
        assert stmt.exclusive is False

        # Full spelling
        stmt2 = analyze_first_command("KVALUE Y")
        assert isinstance(stmt2, MKValueStatement)
        assert stmt2.targets[0].name == "Y"

        # No arguments (kill all values)
        stmt3 = analyze_first_command("KV")
        assert isinstance(stmt3, MKValueStatement)
        assert stmt3.is_kill_all is True

    def test_kvalue_expression_analysis(self):
        """KVALUE expression is analyzed correctly (§8.2.21).

        Verifies exclusive and selective forms work.
        """
        # Exclusive form
        stmt = analyze_first_command("KV (A,B)")
        assert isinstance(stmt, MKValueStatement)
        assert stmt.exclusive is True
        assert "A" in stmt.except_list
        assert "B" in stmt.except_list

        # Multiple targets
        stmt2 = analyze_first_command("KV X,Y,Z")
        assert isinstance(stmt2, MKValueStatement)
        assert len(stmt2.targets) == 3

        # Subscripted target
        stmt3 = analyze_first_command("KV X(1,2)")
        assert isinstance(stmt3, MKValueStatement)
        assert len(stmt3.targets) == 1
        assert len(stmt3.targets[0].subscripts) == 2
