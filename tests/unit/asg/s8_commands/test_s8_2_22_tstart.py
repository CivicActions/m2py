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


@pytest.mark.asg
class TestTstartCompoundParams:
    """Tests for TSTART compound parenthesized parameters (§8.2.22, GAP-003h).

    TSTART supports compound parameter forms where multiple params are
    grouped in parentheses separated by colons: (serial:t="BA")

    This tests the _analyze_TStartParamInner path in semantic_analyzer.py.
    """

    def test_tstart_compound_serial_transactionid(self):
        """TSTART with compound (serial:t=value) parameter form.

        Example: TS ():(serial:t="BA") - both serial and transaction ID in one paren.
        """
        stmt = analyze_first_command('TS ():(serial:t="BA")')

        assert isinstance(stmt, MTStartStatement)
        assert len(stmt.parameters) == 2

        # First param should be SERIAL
        param_names = [p.name.upper() for p in stmt.parameters]
        assert "SERIAL" in param_names or "S" in param_names

        # Second param should be T with value
        t_param = next(
            (p for p in stmt.parameters if p.name.upper() in ("T", "TRANSACTIONID")),
            None,
        )
        assert t_param is not None
        assert t_param.value is not None
        assert t_param.value.value == "BA"

    def test_tstart_compound_abbreviated(self):
        """TSTART with abbreviated compound parameters.

        Example: TS ():(s:t="X") - abbreviated serial and transaction ID.
        """
        stmt = analyze_first_command('TS ():(s:t="X")')

        assert isinstance(stmt, MTStartStatement)
        assert len(stmt.parameters) == 2

        # Check both params are captured
        param_names = [p.name.lower() for p in stmt.parameters]
        assert "s" in param_names
        assert "t" in param_names

    def test_tstart_single_parenthesized_param(self):
        """TSTART with single parenthesized parameter.

        Example: TS ():(serial) - single param in parens.
        """
        stmt = analyze_first_command("TS ():(serial)")

        assert isinstance(stmt, MTStartStatement)
        assert len(stmt.parameters) == 1
        assert stmt.parameters[0].name.upper() in ("SERIAL", "S")

    def test_tstart_compound_with_restart_vars(self):
        """TSTART with restart vars and compound params.

        Example: TS (A,B):(s:t="ID1")
        """
        stmt = analyze_first_command('TS (A,B):(s:t="ID1")')

        assert isinstance(stmt, MTStartStatement)
        # Restart vars
        assert len(stmt.restart_vars) == 2
        var_names = [v.name for v in stmt.restart_vars]
        assert "A" in var_names
        assert "B" in var_names

        # Compound params
        assert len(stmt.parameters) == 2
        param_names = [p.name.lower() for p in stmt.parameters]
        assert "s" in param_names
        assert "t" in param_names
