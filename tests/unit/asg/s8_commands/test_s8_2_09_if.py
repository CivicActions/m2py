"""Tests for IF command ASG analysis (§8.2.9).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.9

Migrated from: tests/unit/test_command_analysis.py::TestIfStatementAnalysis
"""

import pytest
from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MIfStatement


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestIfCommandAnalysis:
    """ASG-level tests for IF command analysis (§8.2.9).

    Migrated from: tests/unit/test_command_analysis.py::TestIfStatementAnalysis
    """

    def test_if_with_condition(self):
        """IF X produces MIfStatement with condition (§8.2.9).

        Migrated from: test_command_analysis.py::TestIfStatementAnalysis::test_if_with_condition
        """
        stmt = analyze_first_command("I X")

        assert isinstance(stmt, MIfStatement)
        assert stmt.condition is not None

    def test_argumentless_if(self):
        """IF (argumentless) produces MIfStatement with no condition (§8.2.9).

        Migrated from: test_command_analysis.py::TestIfStatementAnalysis::test_argumentless_if
        """
        stmt = analyze_first_command("I")

        assert isinstance(stmt, MIfStatement)
        assert stmt.condition is None

    # ---- Stub tests for unimplemented features ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: IF $TEST modification")
    def test_if_test_modification(self, analyze_routine):
        """IF modifies $TEST correctly (§8.2.9)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: IF control flow")
    def test_if_control_flow(self, analyze_routine):
        """IF control flow impact is tracked (§8.2.9)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: IF multiple conditions")
    def test_if_multiple_conditions(self, analyze_routine):
        """IF with multiple comma-separated conditions is analyzed (§8.2.9)."""
        pytest.fail("Stub - implement test")
