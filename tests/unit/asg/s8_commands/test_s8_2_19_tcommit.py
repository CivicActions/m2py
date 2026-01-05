"""Tests for TCOMMIT command ASG analysis (§8.2.19).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.19
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MTCommitStatement


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestTcommitCommandAnalysis:
    """ASG-level tests for TCOMMIT command analysis (§8.2.19)."""

    def test_tcommit_tlevel_tracking(self):
        """TCOMMIT decrements $TLEVEL (§8.2.19).

        Verifies that TCOMMIT produces MTCommitStatement with correct structure
        for tracking $TLEVEL changes. Note: Actual $TLEVEL tracking is runtime;
        this verifies ASG structure supports such tracking.
        """
        # Basic TCOMMIT
        stmt = analyze_first_command("TC")
        assert isinstance(stmt, MTCommitStatement)

        # Full keyword TCOMMIT
        stmt2 = analyze_first_command("TCOMMIT")
        assert isinstance(stmt2, MTCommitStatement)

        # TCOMMIT with postcondition
        stmt3 = analyze_first_command("TC:cond")
        assert isinstance(stmt3, MTCommitStatement)
        assert stmt3.postcondition is not None

    def test_tcommit_transaction_boundary(self):
        """TCOMMIT marks transaction boundary (§8.2.19).

        Verifies that TCOMMIT ASG structure identifies it as a transaction boundary.
        """
        stmt = analyze_first_command("TCOMMIT")
        assert isinstance(stmt, MTCommitStatement)

        # TCOMMIT is a transaction boundary command
        assert type(stmt).__name__ == "MTCommitStatement"

        # TCOMMIT has no arguments (unlike TSTART)
        # It simply commits the current transaction level
