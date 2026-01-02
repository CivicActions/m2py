"""Tests for QUIT command ASG analysis (§8.2.16).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.16

Migrated from: tests/unit/test_command_analysis.py::TestQuitStatementAnalysis
"""

import pytest
from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MQuitStatement
from m2py.asg.expressions import MVariable, MBinaryOp


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestQuitCommandAnalysis:
    """ASG-level tests for QUIT command analysis (§8.2.16).

    Migrated from: tests/unit/test_command_analysis.py::TestQuitStatementAnalysis
    """

    def test_simple_quit(self):
        """Q produces MQuitStatement with no return value (§8.2.16).

        Migrated from: test_command_analysis.py::TestQuitStatementAnalysis::test_simple_quit
        """
        stmt = analyze_first_command("Q")

        assert isinstance(stmt, MQuitStatement)
        assert stmt.return_value is None

    def test_quit_with_value(self):
        """Q X produces MQuitStatement with return value (§8.2.16).

        Migrated from: test_command_analysis.py::TestQuitStatementAnalysis::test_quit_with_value
        """
        stmt = analyze_first_command("Q X")

        assert isinstance(stmt, MQuitStatement)
        assert stmt.return_value is not None
        assert isinstance(stmt.return_value, MVariable)
        assert stmt.return_value.name == "X"

    def test_quit_with_expression(self):
        """Q X+1 produces MQuitStatement with binary expression (§8.2.16).

        Migrated from: test_command_analysis.py::TestQuitStatementAnalysis::test_quit_with_expression
        """
        stmt = analyze_first_command("Q X+1")

        assert isinstance(stmt, MQuitStatement)
        assert stmt.return_value is not None
        assert isinstance(stmt.return_value, MBinaryOp)

    # ---- Stub tests for unimplemented features ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: QUIT control flow")
    def test_quit_control_flow(self, analyze_routine):
        """QUIT terminates current context (§8.2.16)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: QUIT scope cleanup")
    def test_quit_scope_cleanup(self, analyze_routine):
        """QUIT triggers scope cleanup (§8.2.16)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: QUIT from FOR")
    def test_quit_from_for(self, analyze_routine):
        """QUIT from FOR loop is analyzed (§8.2.16)."""
        pytest.fail("Stub - implement test")
