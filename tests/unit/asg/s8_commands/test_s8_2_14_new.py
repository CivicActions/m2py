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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW variable scoping verification")
    def test_new_variable_scoping(self, analyze_routine):
        """NEW creates new variable scope (§8.2.14, FR-014)."""
        pytest.fail(
            "Stub - implement test for verifying NEW affects variable scope tracking"
        )

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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW scope lifetime")
    def test_new_scope_lifetime(self, analyze_routine):
        """NEW scope lifetime is tracked until QUIT (§8.2.14)."""
        pytest.fail("Stub - implement test")
