"""Tests for TRESTART command parsing (§8.2.20).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.20
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg.statements import MTRestartStatement


@pytest.mark.parser
class TestTrestartCommandParsing:
    """Parser-level tests for TRESTART command (§8.2.20)."""

    def test_trestart_basic(self):
        """TRESTART parses correctly to MTRestartStatement (§8.2.20)."""
        parser = MUMPSParser()
        source = "TEST\tTRE\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTRestartStatement)

    def test_trestart_full_keyword(self):
        """TRESTART with full keyword parses correctly (§8.2.20)."""
        parser = MUMPSParser()
        source = "TEST\tTRESTART\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTRestartStatement)
