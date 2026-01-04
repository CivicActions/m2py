"""Tests for Transaction Processing parsing (§6.3.1).

Tests verify the textX grammar correctly captures transaction commands.

Reference: MUMPS 1995 ANSI Standard, Section 6.3.1
"""

import pytest

from m2py.asg import MTCommitStatement, MTStartStatement


@pytest.mark.parser
class TestTransactionProcessingParsing:
    """Parser-level tests for Transaction Processing (§6.3.1).

    Transaction commands: TSTART, TCOMMIT, TROLLBACK, TRESTART
    Cross-references: test_s8_2_19_tcommit.py, test_s8_2_22_tstart.py, etc.
    """

    def test_tstart_basic(self, parse_line):
        """TSTART parses correctly (§6.3.1 Transaction processing)."""
        result = parse_line(" TSTART")
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        assert isinstance(stmt, MTStartStatement)

    def test_nested_transactions(self, parse_mumps):
        """Nested TSTART/TCOMMIT structure parses correctly (§6.3.1).

        MUMPS allows nested transactions. Each TSTART must have a matching TCOMMIT.
        """
        result = parse_mumps(
            "TEST\n TSTART\n S X=1\n TSTART\n S Y=2\n TCOMMIT\n TCOMMIT\n Q"
        )
        assert result is not None
        stmts = result.labels[0].body.statements
        # TSTART, SET, TSTART, SET, TCOMMIT, TCOMMIT, QUIT
        assert len(stmts) == 7
        assert isinstance(stmts[0], MTStartStatement)
        assert isinstance(stmts[2], MTStartStatement)
        assert isinstance(stmts[4], MTCommitStatement)
        assert isinstance(stmts[5], MTCommitStatement)

    def test_transaction_with_restart(self, parse_mumps):
        """Transaction with restart variable parses correctly (§6.3.1).

        TSTART can specify variables to restore on TRESTART.
        """
        result = parse_mumps("TEST\n TSTART (X,Y)\n S X=1\n TCOMMIT\n Q")
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        assert isinstance(stmt, MTStartStatement)
        # restart_vars contains the variables to restore
        assert len(stmt.restart_vars) == 2
        assert stmt.restart_vars[0].name == "X"
        assert stmt.restart_vars[1].name == "Y"
