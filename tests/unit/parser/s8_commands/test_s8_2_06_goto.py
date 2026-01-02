"""Tests for GOTO command parsing (§8.2.6).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.6
"""

import pytest


@pytest.mark.parser
class TestGotoCommandParsing:
    """Parser-level tests for GOTO command (§8.2.6)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: GOTO with label")
    def test_goto_with_label(self, parse_line):
        """GOTO LABEL parses correctly (§8.2.6)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: GOTO with external routine")
    def test_goto_external_routine(self, parse_line):
        """GOTO LABEL^ROUTINE parses correctly (§8.2.6)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: GOTO with offset")
    def test_goto_with_offset(self, parse_line):
        """GOTO LABEL+3 parses correctly (§8.2.6)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: GOTO with postcondition")
    def test_goto_with_postcondition(self, parse_line):
        """GOTO:condition LABEL parses correctly (§8.2.6)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: GOTO abbreviated")
    def test_goto_abbreviated(self, parse_line):
        """G abbreviation parses correctly (§8.2.6)."""
        pytest.fail("Stub - implement test")
