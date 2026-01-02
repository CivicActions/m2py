"""Tests for ELSE command parsing (§8.2.4).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.4
"""

import pytest


@pytest.mark.parser
class TestElseCommandParsing:
    """Parser-level tests for ELSE command (§8.2.4)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ELSE basic form")
    def test_else_basic(self, parse_line):
        """ELSE command parses correctly (§8.2.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ELSE abbreviated")
    def test_else_abbreviated(self, parse_line):
        """E abbreviation parses correctly (§8.2.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ELSE with commands")
    def test_else_with_commands(self, parse_line):
        """ELSE followed by commands parses correctly (§8.2.4)."""
        pytest.fail("Stub - implement test")
