"""Tests for ZLINK command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZlinkParsing:
    """Parser-level tests for ZLINK command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZLINK parsing")
    def test_zlink_basic(self, parse_line):
        """ZLINK parses without error."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZLINK with routine")
    def test_zlink_with_routine(self, parse_line):
        """ZLINK with routine name parses correctly."""
        pytest.fail("Stub - implement test")
