"""Tests for ZALLOCATE/ZDEALLOCATE command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZallocateParsing:
    """Parser-level tests for ZALLOCATE/ZDEALLOCATE command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZALLOCATE parsing")
    def test_zallocate_basic(self, parse_line):
        """ZALLOCATE parses without error."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZDEALLOCATE parsing")
    def test_zdeallocate_basic(self, parse_line):
        """ZDEALLOCATE parses without error."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZALLOCATE with timeout")
    def test_zallocate_with_timeout(self, parse_line):
        """ZALLOCATE with timeout parses correctly."""
        pytest.fail("Stub - implement test")
