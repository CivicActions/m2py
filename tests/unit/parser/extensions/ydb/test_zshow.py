"""Tests for ZSHOW command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZshowParsing:
    """Parser-level tests for ZSHOW command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZSHOW parsing")
    def test_zshow_basic(self, parse_line):
        """ZSHOW parses without error."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZSHOW with codes")
    def test_zshow_with_codes(self, parse_line):
        """ZSHOW with display codes parses correctly."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZSHOW to variable")
    def test_zshow_to_variable(self, parse_line):
        """ZSHOW with target variable parses correctly."""
        pytest.fail("Stub - implement test")
