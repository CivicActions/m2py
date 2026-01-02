"""Tests for FOR command ASG analysis (§8.2.5).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.5

Migrated from: tests/unit/test_command_analysis.py::TestForStatementAnalysis
"""

import pytest
from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MForStatement
from m2py.asg.enums import ForLoopType, ForParamType


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestForCommandAnalysis:
    """ASG-level tests for FOR command analysis (§8.2.5).

    Migrated from: tests/unit/test_command_analysis.py::TestForStatementAnalysis
    """

    def test_argumentless_for(self):
        """F produces argumentless FOR (§8.2.5).

        Migrated from: test_command_analysis.py::TestForStatementAnalysis::test_argumentless_for
        """
        stmt = analyze_first_command("F")

        assert isinstance(stmt, MForStatement)
        assert stmt.loop_var is None or stmt.loop_var == ""
        assert len(stmt.parameters) == 0
        assert stmt.loop_type == ForLoopType.ARGUMENTLESS

    def test_for_with_range(self):
        """F I=1:1:10 produces bounded FOR (§8.2.5).

        Migrated from: test_command_analysis.py::TestForStatementAnalysis::test_for_with_range
        """
        stmt = analyze_first_command("F I=1:1:10")

        assert isinstance(stmt, MForStatement)
        assert stmt.loop_var.name == "I"
        assert len(stmt.parameters) == 1
        assert stmt.parameters[0].param_type == ForParamType.RANGE
        assert stmt.loop_type == ForLoopType.BOUNDED

    def test_for_with_values(self):
        """F I=1,2,3 produces value list FOR (§8.2.5).

        Migrated from: test_command_analysis.py::TestForStatementAnalysis::test_for_with_values
        """
        stmt = analyze_first_command("F I=1,2,3")

        assert isinstance(stmt, MForStatement)
        assert stmt.loop_var.name == "I"
        assert len(stmt.parameters) == 3
        assert all(p.param_type == ForParamType.VALUE for p in stmt.parameters)
        assert stmt.loop_type == ForLoopType.STRING_LIST

    def test_for_open_ended(self):
        """F I=1:1 produces open-ended FOR (§8.2.5).

        Migrated from: test_command_analysis.py::TestForStatementAnalysis::test_for_open_ended
        """
        stmt = analyze_first_command("F I=1:1")

        assert isinstance(stmt, MForStatement)
        assert stmt.loop_var.name == "I"
        assert stmt.loop_type == ForLoopType.OPEN_ENDED

    # ---- Stub tests for unimplemented features ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR loop variable")
    def test_for_loop_variable(self, analyze_routine):
        """FOR loop variable is tracked (§8.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR nested loops")
    def test_for_nested_loops(self, analyze_routine):
        """Nested FOR loops are correctly analyzed (§8.2.5)."""
        pytest.fail("Stub - implement test")
