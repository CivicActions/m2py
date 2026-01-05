"""Tests for NEW command ASG analysis (§8.2.14).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.14
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MNewStatement


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestNewCommandAnalysis:
    """ASG-level tests for NEW command analysis (§8.2.14)."""

    def test_new_simple_variable(self):
        """N X produces MNewStatement with single variable (§8.2.14)."""
        stmt = analyze_first_command("N X")

        assert isinstance(stmt, MNewStatement)
        assert "X" in stmt.variables

    def test_new_multiple_variables(self):
        """N X,Y,Z multiple variables is analyzed (§8.2.14)."""
        stmt = analyze_first_command("N X,Y,Z")

        assert isinstance(stmt, MNewStatement)
        assert len(stmt.variables) == 3

    def test_new_variable_scoping(self):
        """NEW creates new variable scope (§8.2.14, FR-014).

        Verifies that NEW command captures variable names for scope tracking:
        - Variables list contains the NEW'd variable names
        - Multiple NEW'd variables are all captured
        - NEW with exclusive form tracks except_list for scope analysis
        """
        # Single variable NEW
        stmt = analyze_first_command("N X")
        assert isinstance(stmt, MNewStatement)
        assert "X" in stmt.variables
        assert len(stmt.variables) == 1

        # Multiple variables NEW
        stmt2 = analyze_first_command("N A,B,C")
        assert isinstance(stmt2, MNewStatement)
        assert len(stmt2.variables) == 3
        assert "A" in stmt2.variables
        assert "B" in stmt2.variables
        assert "C" in stmt2.variables

        # Exclusive NEW - except_list contains preserved variables
        stmt3 = analyze_first_command("N (X,Y)")
        assert isinstance(stmt3, MNewStatement)
        assert stmt3.exclusive is True
        # Variables that should NOT be NEW'd are in except_list
        assert hasattr(stmt3, "except_list")
        assert len(stmt3.except_list) == 2

    def test_new_exclusive_form(self):
        """NEW (X,Y) exclusive form is analyzed (§8.2.14)."""
        # NEW exclusive form preserves only listed variables
        stmt = analyze_first_command("N (X,Y)")
        assert isinstance(stmt, MNewStatement)
        assert stmt.exclusive is True

        # In exclusive form, variables list may be empty (preserved in except_list)
        # The except_list contains variables to NOT new
        assert hasattr(stmt, "except_list")

        # Regular NEW is not exclusive
        stmt2 = analyze_first_command("N A,B")
        assert isinstance(stmt2, MNewStatement)
        assert stmt2.exclusive is False
        assert len(stmt2.variables) == 2

    def test_new_scope_lifetime(self):
        """NEW scope lifetime is tracked until QUIT (§8.2.14).

        Verifies that the NEW statement captures enough information
        for scope tracking to determine which variables need cleanup on QUIT.

        Note: Actual scope cleanup tracking requires runtime/flow analysis;
        this test verifies the ASG structure supports such analysis.
        """
        # NEW captures variable names for scope tracking
        stmt = analyze_first_command("N X,Y,Z")
        assert isinstance(stmt, MNewStatement)

        # All NEW'd variables accessible for scope analysis
        new_vars = stmt.variables
        assert len(new_vars) == 3
        assert set(new_vars) == {"X", "Y", "Z"}

        # Exclusive NEW preserves only listed variables - others get NEW'd
        stmt2 = analyze_first_command("N (KEEP)")
        assert isinstance(stmt2, MNewStatement)
        assert stmt2.exclusive is True
        # except_list contains variables to preserve (not NEW)
        assert len(stmt2.except_list) == 1

        # Empty exclusive NEW (all variables NEW'd except none)
        # This is the argumentless NEW case
        stmt3 = analyze_first_command("N")
        assert isinstance(stmt3, MNewStatement)
        # No specific variables - this NEWs all in current scope
