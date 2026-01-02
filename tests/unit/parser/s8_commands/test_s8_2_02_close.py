"""Tests for CLOSE command parsing (§8.2.2).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.2
"""

import pytest


@pytest.mark.parser
class TestCloseCommandParsing:
    """Parser-level tests for CLOSE command (§8.2.2)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: CLOSE basic form")
    def test_close_basic(self, parse_line):
        """CLOSE device parses correctly (§8.2.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: CLOSE with parameters")
    def test_close_with_parameters(self, parse_line):
        """CLOSE device:params parses correctly (§8.2.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: CLOSE multiple devices")
    def test_close_multiple_devices(self, parse_line):
        """CLOSE dev1,dev2 parses correctly (§8.2.2)."""
        pytest.fail("Stub - implement test")
