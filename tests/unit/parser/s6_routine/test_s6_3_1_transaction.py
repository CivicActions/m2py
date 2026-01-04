"""Tests for Transaction Processing parsing (§6.3.1).

Tests verify the textX grammar correctly captures transaction commands.

Reference: MUMPS 1995 ANSI Standard, Section 6.3.1
"""

import pytest

from m2py.asg import MTStartStatement


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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: nested transactions")
    def test_nested_transactions(self, parse_mumps):
        """Nested TSTART/TCOMMIT structure parses correctly (§6.3.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: transaction with restart")
    def test_transaction_with_restart(self, parse_mumps):
        """Transaction with restart variable parses correctly (§6.3.1)."""
        pytest.fail("Stub - implement test")
