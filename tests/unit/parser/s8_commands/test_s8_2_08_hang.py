"""Tests for HANG command parsing (§8.2.8).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.8
"""

import pytest


@pytest.mark.parser
class TestHangCommandParsing:
    """Parser-level tests for HANG command (§8.2.8)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: HANG basic form")
    def test_hang_basic(self, parse_line):
        """HANG seconds parses correctly (§8.2.8)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: HANG abbreviated")
    def test_hang_abbreviated(self, parse_line):
        """H seconds abbreviation parses correctly (§8.2.8)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: HANG with decimal")
    def test_hang_with_decimal(self, parse_line):
        """HANG 0.5 decimal seconds parses correctly (§8.2.8)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: HANG with expression")
    def test_hang_with_expression(self, parse_line):
        """HANG X+Y expression parses correctly (§8.2.8)."""
        pytest.fail("Stub - implement test")
