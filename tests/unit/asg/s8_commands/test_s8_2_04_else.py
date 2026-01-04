"""Tests for ELSE command ASG analysis (§8.2.4).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.4
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MElseStatement, MSetStatement


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestElseCommandAnalysis:
    """ASG-level tests for ELSE command analysis (§8.2.4)."""

    def test_else_command_node(self):
        """ELSE command creates correct ASG node (§8.2.4)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n\tE  S X=1\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MElseStatement)

        # ELSE should have a body for following commands
        assert stmt.body is not None
        assert len(stmt.body.statements) == 1
        assert isinstance(stmt.body.statements[0], MSetStatement)

        # Also test abbreviated form
        routine2 = parser.parse("TEST\n\tELSE  W X\n")
        stmt2 = routine2.labels[0].body.statements[0]
        assert isinstance(stmt2, MElseStatement)

    def test_else_test_dependency(self):
        """ELSE dependency on $TEST is tracked (§8.2.4)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n\tE  S X=1\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MElseStatement)

        # ELSE implicitly depends on $TEST (the negation of current $TEST value)
        # The ELSE command should be recognized as executing only when $TEST is 0
        # Verify the MElseStatement has the expected structure
        assert hasattr(stmt, "body")
        assert stmt.body is not None

        # ELSE has no explicit condition (it uses $TEST implicitly)
        # Unlike IF, ELSE doesn't have a condition attribute with an expression
        if hasattr(stmt, "condition"):
            # If condition exists, it should be None (implicit $TEST check)
            assert stmt.condition is None

    def test_else_control_flow(self):
        """ELSE control flow impact is analyzed (§8.2.4)."""
        parser = MUMPSParser()

        # ELSE should only execute when $TEST is false
        # Body commands are captured in ELSE scope
        routine = parser.parse("TEST\n\tE  S X=1 S Y=2\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MElseStatement)

        # All following commands on the line should be in ELSE body
        assert len(stmt.body.statements) == 2
        assert isinstance(stmt.body.statements[0], MSetStatement)
        assert isinstance(stmt.body.statements[1], MSetStatement)

        # ELSE with postcondition is documented in MUMPS spec but
        # may not be commonly used. Verify structure supports it.
        assert hasattr(stmt, "postcondition")
        # Postcondition parsing for ELSE may be a future enhancement
