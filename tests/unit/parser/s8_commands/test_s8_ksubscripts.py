"""Tests for $KEY subscripts parsing (§8.2.20).

Shares section numbering with TRESTART.
Reference: MUMPS 1995 ANSI Standard, Section 8.2.20
"""

import pytest


@pytest.mark.parser
class TestKSubscriptsParsing:
    """Parser-level tests for $KEY subscripts (§8.2.20)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KSUBSCRIPTS basic form")
    def test_ksubscripts_basic(self, parse_line):
        """KSUBSCRIPTS parses correctly (§8.2.20)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KSUBSCRIPTS with arguments")
    def test_ksubscripts_with_arguments(self, parse_line):
        """KSUBSCRIPTS with arguments parses correctly (§8.2.20)."""
        pytest.fail("Stub - implement test")
