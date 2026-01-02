"""Tests for ZMESSAGE command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZmessageParsing:
    """Parser-level tests for ZMESSAGE command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZMESSAGE parsing")
    def test_zmessage_basic(self, parse_line):
        """ZMESSAGE parses without error."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZMESSAGE with code")
    def test_zmessage_with_code(self, parse_line):
        """ZMESSAGE with message code parses correctly."""
        pytest.fail("Stub - implement test")
