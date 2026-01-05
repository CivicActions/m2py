"""Tests for TROLLBACK command ASG analysis (§8.2.21).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.21
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MTRollbackStatement
from m2py.asg.expressions import MLiteral


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestTrollbackCommandAnalysis:
    """ASG-level tests for TROLLBACK command analysis (§8.2.21)."""

    def test_trollback_tlevel_tracking(self):
        """TROLLBACK modifies $TLEVEL (§8.2.21).

        Verifies that TROLLBACK produces MTRollbackStatement with correct structure
        for tracking $TLEVEL changes. Note: Actual $TLEVEL tracking is runtime;
        this verifies ASG structure supports such tracking.
        """
        # Basic TROLLBACK - rolls back to level 0
        stmt = analyze_first_command("TRO")
        assert isinstance(stmt, MTRollbackStatement)
        assert stmt.level is None  # No level = roll back all

        # Full keyword TROLLBACK
        stmt2 = analyze_first_command("TROLLBACK")
        assert isinstance(stmt2, MTRollbackStatement)

        # TROLLBACK with postcondition
        stmt3 = analyze_first_command("TRO:cond")
        assert isinstance(stmt3, MTRollbackStatement)
        assert stmt3.postcondition is not None

    def test_trollback_variable_restoration(self):
        """TROLLBACK variable restoration is analyzed (§8.2.21).

        Verifies that TROLLBACK ASG structure identifies it as a command
        that restores variable values to their pre-transaction state.
        Note: Actual variable restoration is runtime behavior.
        """
        stmt = analyze_first_command("TRO")
        assert isinstance(stmt, MTRollbackStatement)

        # TROLLBACK is a transaction rollback command
        assert type(stmt).__name__ == "MTRollbackStatement"

        # No level means complete rollback (variables restored)
        assert stmt.level is None

    def test_trollback_to_level(self):
        """TROLLBACK N to specific level is analyzed (§8.2.21).

        Verifies that TROLLBACK with level argument captures the level.
        """
        # TROLLBACK to level 1
        stmt = analyze_first_command("TRO 1")
        assert isinstance(stmt, MTRollbackStatement)
        assert stmt.level is not None
        assert isinstance(stmt.level, MLiteral)
        assert stmt.level.value == "1"

        # TROLLBACK to level 0 (same as no argument)
        stmt2 = analyze_first_command("TRO 0")
        assert isinstance(stmt2, MTRollbackStatement)
        assert stmt2.level is not None
        assert stmt2.level.value == "0"

        # TROLLBACK with $TLEVEL expression
        stmt3 = analyze_first_command("TRO $TLEVEL-1")
        assert isinstance(stmt3, MTRollbackStatement)
        assert stmt3.level is not None
        # Level is captured as string expression
        assert "$TLEVEL-1" in stmt3.level.value
