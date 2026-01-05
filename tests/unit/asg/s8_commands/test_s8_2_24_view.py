"""Tests for VIEW command ASG analysis (§8.2.24).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.24

Note: VIEW keywords are implementation-defined (§8.2.24).
See docs/limitations.md - LIM-005: VIEW Command
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MViewStatement


@pytest.mark.asg
class TestViewStatementASG:
    """Tests for VIEW command ASG field population."""

    def test_view_command_simple(self):
        """VIEW with arguments produces MViewStatement."""
        parser = MUMPSParser()
        routine = parser.parse('TEST\n V "UNDEF"\n')

        label = routine.labels[0]
        assert len(label.body.statements) == 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MViewStatement)
        assert len(stmt.arguments) >= 1

    def test_view_command_with_expression(self):
        """VIEW with variable expression."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n V X\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MViewStatement)
        assert len(stmt.arguments) >= 1

    def test_view_command_with_postcondition(self):
        """VIEW:condition args handles postcondition."""
        parser = MUMPSParser()
        routine = parser.parse('TEST\n V:X>0 "DEBUG"\n')

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MViewStatement)
        assert stmt.postcondition is not None
