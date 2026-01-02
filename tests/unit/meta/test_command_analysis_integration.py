"""Integration tests for command analysis across multiple commands.

Reference: MUMPS 1995 ANSI Standard, Section 8 (Commands)

Migrated from: tests/unit/test_command_analysis.py::TestMultipleCommandsAnalysis
"""

import pytest
from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import (
    MSetStatement,
    MWriteStatement,
    MQuitStatement,
)


@pytest.mark.asg
class TestMultipleCommandsAnalysis:
    """Integration tests for analyzing multiple commands in sequence.

    Migrated from: tests/unit/test_command_analysis.py::TestMultipleCommandsAnalysis
    """

    def test_line_with_multiple_commands(self):
        """S X=1 W X Q produces three statements (§8).

        Migrated from: test_command_analysis.py::TestMultipleCommandsAnalysis::test_line_with_multiple_commands
        """
        cmds = parse_commands_from_line("S X=1 W X Q")
        stmts = [analyze_command(cmd) for cmd in cmds]

        assert len(stmts) == 3
        assert isinstance(stmts[0], MSetStatement)
        assert isinstance(stmts[1], MWriteStatement)
        assert isinstance(stmts[2], MQuitStatement)
