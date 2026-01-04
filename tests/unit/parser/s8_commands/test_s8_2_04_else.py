"""Tests for ELSE command parsing (§8.2.4).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.4
"""

import pytest

from m2py.asg import MElseStatement, MIfStatement, MSetStatement, MWriteStatement


@pytest.mark.parser
class TestElseCommandParsing:
    """Parser-level tests for ELSE command (§8.2.4)."""

    def test_else_basic(self, parse_mumps):
        """ELSE command parses correctly (§8.2.4).

        ELSE executes when $TEST is false.
        """
        result = parse_mumps('TEST\n I X=1 W "yes"\n ELSE  W "no"\n Q')
        assert result is not None
        stmts = result.labels[0].body.statements
        assert len(stmts) >= 2
        assert isinstance(stmts[0], MIfStatement)
        assert isinstance(stmts[1], MElseStatement)

    def test_else_abbreviated(self, parse_mumps):
        """E abbreviation parses correctly (§8.2.4).

        E is the standard abbreviation for ELSE.
        """
        result = parse_mumps('TEST\n I X=1 W "yes"\n E  W "no"\n Q')
        assert result is not None
        stmts = result.labels[0].body.statements
        assert isinstance(stmts[1], MElseStatement)

    def test_else_with_commands(self, parse_mumps):
        """ELSE followed by commands parses correctly (§8.2.4).

        Commands after ELSE are in the ELSE body.
        """
        result = parse_mumps('TEST\n I X=1 W "yes"\n E  S Y=2 W "no"\n Q')
        assert result is not None
        else_stmt = result.labels[0].body.statements[1]
        assert isinstance(else_stmt, MElseStatement)
        # ELSE has a body with commands
        assert else_stmt.body is not None
        assert len(else_stmt.body.statements) == 2
        assert isinstance(else_stmt.body.statements[0], MSetStatement)
        assert isinstance(else_stmt.body.statements[1], MWriteStatement)
