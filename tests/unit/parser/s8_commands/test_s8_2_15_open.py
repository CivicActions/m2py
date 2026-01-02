"""Tests for OPEN command parsing (§8.2.15).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.15
"""

import pytest


@pytest.mark.parser
class TestOpenCommandParsing:
    """Parser-level tests for OPEN command (§8.2.15)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: OPEN basic form")
    def test_open_basic(self, parse_line):
        """OPEN device parses correctly (§8.2.15)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: OPEN with parameters")
    def test_open_with_parameters(self, parse_line):
        """OPEN device:(params) parses correctly (§8.2.15)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: OPEN with timeout")
    def test_open_with_timeout(self, parse_line):
        """OPEN device::timeout parses correctly (§8.2.15)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: OPEN with mnemonic space")
    def test_open_with_mnemonic(self, parse_line):
        """OPEN device:(params):timeout:\"SOCKET\" parses correctly (§8.2.15)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: OPEN multiple devices")
    def test_open_multiple(self, parse_line):
        """OPEN dev1,dev2 multiple devices parses correctly (§8.2.15)."""
        pytest.fail("Stub - implement test")
