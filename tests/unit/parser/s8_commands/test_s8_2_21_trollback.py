"""Tests for TROLLBACK command parsing (§8.2.21).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.21
Migrated from: tests/unit/test_parser.py::TestTransactionCommands (TROLLBACK tests)
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg.statements import MTRollbackStatement


@pytest.mark.parser
class TestTrollbackCommandParsing:
    """Parser-level tests for TROLLBACK command (§8.2.21).

    Migrated from: tests/unit/test_parser.py::TestTransactionCommands
    """

    def test_trollback_basic(self):
        """T94.14: Basic TROLLBACK command should parse to MTRollbackStatement (§8.2.21)."""
        parser = MUMPSParser()
        source = "TEST\tTRO\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTRollbackStatement)
        assert stmt.level is None

    def test_trollback_full_keyword(self):
        """T94.14: TROLLBACK with full keyword should parse (§8.2.21)."""
        parser = MUMPSParser()
        source = "TEST\tTROLLBACK\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTRollbackStatement)

    def test_trollback_with_level(self):
        """T94.14: TROLLBACK with level argument should parse (§8.2.21)."""
        parser = MUMPSParser()
        source = "TEST\tTRO 1\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTRollbackStatement)
        assert stmt.level is not None

    def test_trollback_with_postcondition(self):
        """T94.14: TROLLBACK with postcondition should parse (§8.2.21)."""
        parser = MUMPSParser()
        source = "TEST\tTRO:X=1\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTRollbackStatement)
        assert stmt.postcondition is not None
