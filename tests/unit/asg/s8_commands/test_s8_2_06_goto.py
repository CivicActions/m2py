"""Tests for GOTO command ASG analysis (§8.2.6).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.6

Migrated from: tests/unit/test_command_analysis.py::TestGotoStatementAnalysis
"""

import pytest
from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MGotoStatement
from m2py.asg.expressions import MGlobal


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestGotoCommandAnalysis:
    """ASG-level tests for GOTO command analysis (§8.2.6).

    Migrated from: tests/unit/test_command_analysis.py::TestGotoStatementAnalysis
    """

    def test_simple_goto(self):
        """G LABEL produces MGotoStatement (§8.2.6).

        Migrated from: test_command_analysis.py::TestGotoStatementAnalysis::test_simple_goto
        """
        stmt = analyze_first_command("G LABEL")

        assert isinstance(stmt, MGotoStatement)
        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "LABEL"

    def test_goto_with_routine(self):
        """G LABEL^ROUTINE produces target with routine (§8.2.6).

        Migrated from: test_command_analysis.py::TestGotoStatementAnalysis::test_goto_with_routine
        """
        stmt = analyze_first_command("G LABEL^ROUTINE")

        assert isinstance(stmt, MGotoStatement)
        assert stmt.targets[0].name == "LABEL"
        assert stmt.targets[0].routine == "ROUTINE"

    def test_goto_with_subscripted_global_offset(self):
        """G LABEL+^DATA(1)^ROUTINE - offset with SubscriptedGlobal becomes MGlobal (§8.2.6).

        Migrated from: test_command_analysis.py::TestGotoStatementAnalysis::test_goto_with_subscripted_global_offset
        """
        stmt = analyze_first_command("G LABEL+^DATA(1)^ROUTINE")

        assert isinstance(stmt, MGotoStatement)
        target = stmt.targets[0]
        assert target.name == "LABEL"
        assert target.routine == "ROUTINE"
        # The offset is an MGlobal (converted from SubscriptedGlobal)
        assert isinstance(target.offset, MGlobal)
        assert target.offset.name == "DATA"
        assert len(target.offset.subscripts) == 1

    # ---- Stub tests for unimplemented features ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: GOTO target resolution")
    def test_goto_target_resolution(self, analyze_routine):
        """GOTO target is resolved to MLabel (§8.2.6)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: GOTO computed target")
    def test_goto_computed_target(self, analyze_routine):
        """GOTO computed target is tracked (§8.2.6)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: GOTO control flow impact")
    def test_goto_control_flow_impact(self, analyze_routine):
        """GOTO control flow impact is analyzed (§8.2.6)."""
        pytest.fail("Stub - implement test")
