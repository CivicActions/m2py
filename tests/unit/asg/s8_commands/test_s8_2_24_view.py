"""Tests for VIEW command ASG analysis (§8.2.24).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.24

Migrated from: tests/unit/test_io_commands.py::TestViewCommand
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MViewStatement


@pytest.mark.asg
class TestViewCommandAnalysis:
    """ASG-level tests for VIEW command analysis (§8.2.24)."""

    def test_view_command_simple(self):
        """VIEW with arguments produces MViewStatement (§8.2.24).

        Migrated from: test_io_commands.py::TestViewCommand::test_view_command_simple
        """
        parser = MUMPSParser()
        routine = parser.parse('TEST\n V "UNDEF"\n')

        label = routine.labels[0]
        assert len(label.body.statements) == 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MViewStatement)
        assert len(stmt.arguments) >= 1

    def test_view_command_with_expression(self):
        """VIEW with variable expression (§8.2.24).

        Migrated from: test_io_commands.py::TestViewCommand::test_view_command_with_expression
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n V X\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MViewStatement)
        assert len(stmt.arguments) >= 1

    def test_view_command_with_postcondition(self):
        """VIEW:condition args handles postcondition (§8.2.24).

        Migrated from: test_io_commands.py::TestViewCommand::test_view_command_with_postcondition
        """
        parser = MUMPSParser()
        routine = parser.parse('TEST\n V:X>0 "DEBUG"\n')

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MViewStatement)
        assert stmt.postcondition is not None

    @pytest.mark.xfail(reason="Used in VistA: VIEW keywords like V 2:5:$C(X)")
    def test_view_implementation_defined(self):
        """VIEW command is implementation-defined but used in VistA (§8.2.24)."""
        pytest.fail("Stub - implement test")
