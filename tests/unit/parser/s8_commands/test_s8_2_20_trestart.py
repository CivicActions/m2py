"""Tests for TRESTART command parsing (§8.2.20).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.20
"""

import pytest


@pytest.mark.parser
class TestTrestartCommandParsing:
    """Parser-level tests for TRESTART command (§8.2.20)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: TRESTART basic form")
    def test_trestart_basic(self, parse_line):
        """TRESTART parses correctly (§8.2.20)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: TRESTART abbreviated")
    def test_trestart_abbreviated(self, parse_line):
        """TRE abbreviation parses correctly (§8.2.20)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: TRESTART with postcondition")
    def test_trestart_with_postcondition(self, parse_line):
        """TRESTART:condition parses correctly (§8.2.20)."""
        pytest.fail("Stub - implement test")
