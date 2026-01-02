"""Tests for ZEDIT command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZeditParsing:
    """Parser-level tests for ZEDIT command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZEDIT parsing")
    def test_zedit_basic(self, parse_line):
        """ZEDIT parses without error."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZEDIT with routine")
    def test_zedit_with_routine(self, parse_line):
        """ZEDIT with routine name parses correctly."""
        pytest.fail("Stub - implement test")
