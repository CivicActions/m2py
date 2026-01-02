"""Tests for ZHALT command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZhaltParsing:
    """Parser-level tests for ZHALT command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZHALT parsing")
    def test_zhalt_basic(self, parse_line):
        """ZHALT parses without error."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZHALT with status")
    def test_zhalt_with_status(self, parse_line):
        """ZHALT with exit status parses correctly."""
        pytest.fail("Stub - implement test")
