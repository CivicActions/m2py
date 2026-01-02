"""Tests for TRESTART command parsing (§8.2.20).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.20
Migrated from: tests/unit/test_parser.py::TestTransactionCommands (TRESTART tests)
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg.statements import MTRestartStatement


@pytest.mark.parser
class TestTrestartCommandParsing:
    """Parser-level tests for TRESTART command (§8.2.20).

    Migrated from: tests/unit/test_parser.py::TestTransactionCommands
    """

    def test_trestart_basic(self):
        """T94.14: Basic TRESTART command should parse to MTRestartStatement (§8.2.20)."""
        parser = MUMPSParser()
        source = "TEST\tTRE\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTRestartStatement)

    def test_trestart_full_keyword(self):
        """T94.14: TRESTART with full keyword should parse (§8.2.20)."""
        parser = MUMPSParser()
        source = "TEST\tTRESTART\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTRestartStatement)
