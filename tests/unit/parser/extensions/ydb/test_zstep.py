"""Tests for ZSTEP command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZstepParsing:
    """Parser-level tests for ZSTEP command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZSTEP parsing")
    def test_zstep_basic(self, parse_line):
        """ZSTEP parses without error."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZSTEP INTO")
    def test_zstep_into(self, parse_line):
        """ZSTEP INTO parses correctly."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZSTEP OVER")
    def test_zstep_over(self, parse_line):
        """ZSTEP OVER parses correctly."""
        pytest.fail("Stub - implement test")
