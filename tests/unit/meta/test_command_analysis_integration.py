"""Integration tests for command analysis across multiple commands."""

import pytest
from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MSetStatement, MWriteStatement, MQuitStatement


@pytest.mark.asg
class TestMultipleCommandsAnalysis:
    """Tests for analyzing multiple commands on a single line."""

    def test_line_with_multiple_commands(self):
        """S X=1 W X Q produces three statements."""
        cmds = parse_commands_from_line("S X=1 W X Q")
        stmts = [analyze_command(cmd) for cmd in cmds]

        assert len(stmts) == 3
        assert isinstance(stmts[0], MSetStatement)
        assert isinstance(stmts[1], MWriteStatement)
        assert isinstance(stmts[2], MQuitStatement)
