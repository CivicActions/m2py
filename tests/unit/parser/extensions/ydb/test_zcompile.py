"""Tests for ZCOMPILE command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZcompileParsing:
    """Parser-level tests for ZCOMPILE command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZCOMPILE parsing")
    def test_zcompile_basic(self, parse_line):
        """ZCOMPILE parses without error."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZCOMPILE with routine")
    def test_zcompile_with_routine(self, parse_line):
        """ZCOMPILE with routine name parses correctly."""
        pytest.fail("Stub - implement test")
