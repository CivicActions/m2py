"""Tests for WRITE command parsing (§8.2.27).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.27

Migrated from:
- tests/unit/test_grammar.py::TestWriteStatementGrammar
- tests/unit/test_line_parser.py::TestParseWriteCommand
"""

import pytest

from m2py.asg import MRoutine
from m2py.asg.expressions import MFormatControl
from m2py.asg.enums import FormatControlType
from m2py.analysis import analyze_command
from m2py.parser import MUMPSParser
from m2py.parser.line_parser import parse_commands_from_line


@pytest.mark.parser
class TestWriteStatementGrammar:
    """Test WRITE command parsing (§8.2.27).

    Migrated from: tests/unit/test_grammar.py::TestWriteStatementGrammar
    """

    def test_simple_write(self):
        """WRITE with single string argument (§8.2.27)."""
        parser = MUMPSParser()
        source = 'LABEL\tW "Hello"\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_write_abbreviated(self):
        """W abbreviation should work same as WRITE (§8.2.27)."""
        parser = MUMPSParser()
        source = "LABEL\tW !!\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_write_format_codes(self):
        """WRITE with format codes (!, #, ?n) (§8.2.27)."""
        parser = MUMPSParser()
        source = 'LABEL\tW !!,"Test",!\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_write_variable(self):
        """WRITE with variable reference (§8.2.27)."""
        parser = MUMPSParser()
        source = "LABEL\tW X\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestParseWriteCommand:
    """Test WRITE command parsing to full-fidelity ASG.

    Migrated from: tests/unit/test_line_parser.py::TestParseWriteCommand
    """

    def test_simple_write(self):
        """W X creates MWriteStatement."""
        cmds = parse_commands_from_line("W X")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert len(stmt.arguments) == 1

    def test_write_string(self):
        """W "Hello" parses string."""
        cmds = parse_commands_from_line('W "Hello"')
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert len(stmt.arguments) == 1

    def test_write_newline(self):
        """W ! parses newline."""
        cmds = parse_commands_from_line("W !")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert isinstance(stmt.arguments[0], MFormatControl)
        assert stmt.arguments[0].control_type == FormatControlType.NEWLINE
