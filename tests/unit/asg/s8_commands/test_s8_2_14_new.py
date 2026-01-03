"""Tests for NEW command ASG analysis (§8.2.14).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.14
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MNewStatement


@pytest.mark.asg
class TestNewCommandAnalysis:
    """ASG-level tests for NEW command analysis (§8.2.14)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW variable scoping")
    def test_new_variable_scoping(self, analyze_routine):
        """NEW creates new variable scope (§8.2.14, FR-014)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW exclusive form")
    def test_new_exclusive_form(self, analyze_routine):
        """NEW (X,Y) exclusive form is analyzed (§8.2.14)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW scope lifetime")
    def test_new_scope_lifetime(self, analyze_routine):
        """NEW scope lifetime is tracked until QUIT (§8.2.14)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW multiple variables")
    def test_new_multiple_variables(self, analyze_routine):
        """NEW X,Y,Z multiple variables is analyzed (§8.2.14)."""
        pytest.fail("Stub - implement test")


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestNewStatementAnalysis:
    """Tests for NEW command analysis."""

    def test_simple_new(self):
        """N X produces MNewStatement."""
        stmt = analyze_first_command("N X")

        assert isinstance(stmt, MNewStatement)
        assert "X" in stmt.variables

    def test_multiple_new(self):
        """N X,Y,Z produces multiple variables."""
        stmt = analyze_first_command("N X,Y,Z")

        assert isinstance(stmt, MNewStatement)
        assert len(stmt.variables) == 3
