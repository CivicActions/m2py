"""Tests for ZTRIGGER command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZtriggerParsing:
    """Parser-level tests for ZTRIGGER command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZTRIGGER parsing")
    def test_ztrigger_basic(self, parse_line):
        """ZTRIGGER parses without error."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZTRIGGER with args")
    def test_ztrigger_with_args(self, parse_line):
        """ZTRIGGER with arguments parses correctly."""
        pytest.fail("Stub - implement test")
