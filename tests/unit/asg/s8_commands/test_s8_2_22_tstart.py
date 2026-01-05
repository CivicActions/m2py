"""Tests for TSTART command ASG analysis (§8.2.22).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.22
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MTStartStatement


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestTstartCommandAnalysis:
    """ASG-level tests for TSTART command analysis (§8.2.22)."""

    def test_tstart_tlevel_tracking(self):
        """TSTART increments $TLEVEL (§8.2.22).

        Verifies that TSTART produces MTStartStatement with correct structure
        for tracking $TLEVEL changes. Note: Actual $TLEVEL tracking is runtime;
        this verifies ASG structure supports such tracking.
        """
        # Basic TSTART - non-restartable
        stmt = analyze_first_command("TS")
        assert isinstance(stmt, MTStartStatement)
        assert stmt.restart_vars == []
        assert stmt.restart_all is False

        # TSTART with postcondition
        stmt2 = analyze_first_command("TS:cond")
        assert isinstance(stmt2, MTStartStatement)
        assert stmt2.postcondition is not None

    def test_tstart_variable_list(self):
        """TSTART (X,Y) variable list is analyzed (§8.2.22).

        Verifies that TSTART with restart variables captures the variable list.
        """
        # Empty restart list - restartable transaction
        stmt = analyze_first_command("TS ()")
        assert isinstance(stmt, MTStartStatement)
        assert stmt.restart_vars == []
        assert stmt.restart_all is False

        # Variables to restore on restart
        stmt2 = analyze_first_command("TS (A,B,C)")
        assert isinstance(stmt2, MTStartStatement)
        assert len(stmt2.restart_vars) == 3
        var_names = [v.name for v in stmt2.restart_vars]
        assert var_names == ["A", "B", "C"]

    def test_tstart_transaction_boundary(self):
        """TSTART marks transaction start boundary (§8.2.22).

        Verifies that TSTART ASG structure identifies it as a transaction boundary.
        """
        stmt = analyze_first_command("TSTART")
        assert isinstance(stmt, MTStartStatement)

        # TSTART is a transaction boundary command
        assert type(stmt).__name__ == "MTStartStatement"

        # Can have parameters that affect transaction behavior
        stmt2 = analyze_first_command("TS ():S")
        assert isinstance(stmt2, MTStartStatement)
        assert len(stmt2.parameters) >= 1

    def test_tstart_restart_option(self):
        """TSTART RESTART option is analyzed (§8.2.22).

        Verifies that TSTART captures restart options:
        - * = restore all local variables
        - () = restartable but no specific variables
        - (A,B) = restore specific variables
        """
        # Restart all variables
        stmt = analyze_first_command("TS *")
        assert isinstance(stmt, MTStartStatement)
        assert stmt.restart_all is True

        # Restartable with SERIAL parameter
        stmt2 = analyze_first_command("TS ():SERIAL")
        assert isinstance(stmt2, MTStartStatement)
        assert len(stmt2.parameters) >= 1
        # Find SERIAL parameter
        serial_param = next(
            (p for p in stmt2.parameters if p.name.upper() in ("S", "SERIAL")), None
        )
        assert serial_param is not None
