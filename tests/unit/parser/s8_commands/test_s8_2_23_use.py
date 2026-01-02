"""Tests for USE command parsing (§8.2.23).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.23
"""

import pytest


@pytest.mark.parser
class TestUseCommandParsing:
    """Parser-level tests for USE command (§8.2.23)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: USE basic form")
    def test_use_basic(self, parse_line):
        """USE device parses correctly (§8.2.23)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: USE with parameters")
    def test_use_with_parameters(self, parse_line):
        """USE device:(params) parses correctly (§8.2.23)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: USE with mnemonic space")
    def test_use_with_mnemonic(self, parse_line):
        """USE device:(params):\"SOCKET\" parses correctly (§8.2.23)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: USE abbreviated")
    def test_use_abbreviated(self, parse_line):
        """U abbreviation parses correctly (§8.2.23)."""
        pytest.fail("Stub - implement test")
