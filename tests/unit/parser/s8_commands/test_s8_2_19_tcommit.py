"""Tests for TCOMMIT command parsing (§8.2.19).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.19
Migrated from: tests/unit/test_parser.py::TestTransactionCommands (TCOMMIT tests)
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg.statements import MTCommitStatement


@pytest.mark.parser
class TestTcommitCommandParsing:
    """Parser-level tests for TCOMMIT command (§8.2.19).

    Migrated from: tests/unit/test_parser.py::TestTransactionCommands
    """

    def test_tcommit_basic(self):
        """T94.14: Basic TCOMMIT command should parse to MTCommitStatement (§8.2.19)."""
        parser = MUMPSParser()
        source = "TEST\tTC\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTCommitStatement)

    def test_tcommit_full_keyword(self):
        """T94.14: TCOMMIT with full keyword should parse (§8.2.19)."""
        parser = MUMPSParser()
        source = "TEST\tTCOMMIT\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTCommitStatement)

    def test_tcommit_with_postcondition(self):
        """T94.14: TCOMMIT with postcondition should parse (§8.2.19)."""
        parser = MUMPSParser()
        source = "TEST\tTC:X=1\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTCommitStatement)
        assert stmt.postcondition is not None
