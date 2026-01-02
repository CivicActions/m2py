"""Tests for ZGOTO command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZgotoParsing:
    """Parser-level tests for ZGOTO command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZGOTO parsing")
    def test_zgoto_basic(self, parse_line):
        """ZGOTO parses without error."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZGOTO with level")
    def test_zgoto_with_level(self, parse_line):
        """ZGOTO with stack level parses correctly."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZGOTO with entryref")
    def test_zgoto_with_entryref(self, parse_line):
        """ZGOTO with entryref parses correctly."""
        pytest.fail("Stub - implement test")
