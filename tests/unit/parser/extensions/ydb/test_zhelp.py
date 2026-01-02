"""Tests for ZHELP command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZhelpParsing:
    """Parser-level tests for ZHELP command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZHELP parsing")
    def test_zhelp_basic(self, parse_line):
        """ZHELP parses without error."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZHELP with topic")
    def test_zhelp_with_topic(self, parse_line):
        """ZHELP with topic parses correctly."""
        pytest.fail("Stub - implement test")
