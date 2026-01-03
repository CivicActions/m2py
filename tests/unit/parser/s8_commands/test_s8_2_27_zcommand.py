"""Tests for Z-command parsing (§8.2.27).

Z-commands are implementation-defined extensions to standard MUMPS.
Reference: MUMPS 1995 ANSI Standard, Section 8.2.27
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZCommandParsing:
    """Parser-level tests for Z-command syntax (§8.2.27)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: generic Z-command parsing")
    def test_zcommand_generic(self, parse_line):
        """Z-command basic form parses correctly (§8.2.27)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: Z-command with arguments")
    def test_zcommand_with_arguments(self, parse_line):
        """Z-command with arguments parses correctly (§8.2.27)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: unknown Z-command")
    def test_zcommand_unknown(self, parse_line):
        """Unknown Z-command should be accepted for extensibility (§8.2.27)."""
        pytest.fail("Stub - implement test")
