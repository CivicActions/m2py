"""Tests for ZKILL/ZWITHDRAW command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZkillParsing:
    """Parser-level tests for ZKILL/ZWITHDRAW command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZKILL parsing")
    def test_zkill_basic(self, parse_line):
        """ZKILL parses without error."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZWITHDRAW parsing")
    def test_zwithdraw_basic(self, parse_line):
        """ZWITHDRAW parses without error."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZKILL with subscripts")
    def test_zkill_with_subscripts(self, parse_line):
        """ZKILL with subscripted variable parses correctly."""
        pytest.fail("Stub - implement test")
