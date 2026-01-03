"""Tests for TROLLBACK command parsing (§8.2.21).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.21
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg.statements import MTRollbackStatement


@pytest.mark.parser
class TestTrollbackCommandParsing:
    """Parser-level tests for TROLLBACK command (§8.2.21)."""

    def test_trollback_basic(self):
        """TROLLBACK parses correctly to MTRollbackStatement (§8.2.21)."""
        parser = MUMPSParser()
        source = "TEST\tTRO\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTRollbackStatement)
        assert stmt.level is None

    def test_trollback_full_keyword(self):
        """TROLLBACK with full keyword parses correctly (§8.2.21)."""
        parser = MUMPSParser()
        source = "TEST\tTROLLBACK\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTRollbackStatement)

    def test_trollback_with_postcondition(self):
        """TROLLBACK:condition parses correctly (§8.2.21)."""
        parser = MUMPSParser()
        source = "TEST\tTRO:X=1\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTRollbackStatement)
        assert stmt.postcondition is not None

    def test_trollback_to_level(self):
        """TROLLBACK N rollback to level parses correctly (§8.2.21)."""
        parser = MUMPSParser()
        source = "TEST\tTRO 1\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTRollbackStatement)
        assert stmt.level is not None
