"""Tests for TCOMMIT command parsing (§8.2.19).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.19
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg.statements import MTCommitStatement


@pytest.mark.parser
class TestTcommitCommandParsing:
    """Parser-level tests for TCOMMIT command (§8.2.19)."""

    def test_tcommit_basic(self):
        """TCOMMIT parses correctly to MTCommitStatement (§8.2.19)."""
        parser = MUMPSParser()
        source = "TEST\tTC\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTCommitStatement)

    def test_tcommit_full_keyword(self):
        """TCOMMIT with full keyword parses correctly (§8.2.19)."""
        parser = MUMPSParser()
        source = "TEST\tTCOMMIT\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTCommitStatement)

    def test_tcommit_with_postcondition(self):
        """TCOMMIT:condition parses correctly (§8.2.19)."""
        parser = MUMPSParser()
        source = "TEST\tTC:X=1\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTCommitStatement)
        assert stmt.postcondition is not None
