"""Tests for ZCONTINUE command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZcontinueParsing:
    """Parser-level tests for ZCONTINUE command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZCONTINUE parsing")
    def test_zcontinue_basic(self, parse_line):
        """ZCONTINUE parses without error."""
        pytest.fail("Stub - implement test")
