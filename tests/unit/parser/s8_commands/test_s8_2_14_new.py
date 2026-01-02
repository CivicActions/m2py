"""Tests for NEW command parsing (§8.2.14).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.14
"""

import pytest


@pytest.mark.parser
class TestNewCommandParsing:
    """Parser-level tests for NEW command (§8.2.14)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW single variable")
    def test_new_single_variable(self, parse_line):
        """NEW X parses correctly (§8.2.14)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW multiple variables")
    def test_new_multiple_variables(self, parse_line):
        """NEW X,Y,Z multiple variables parses correctly (§8.2.14)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW exclusive form")
    def test_new_exclusive(self, parse_line):
        """NEW (X,Y) exclusive NEW parses correctly (§8.2.14)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW argumentless")
    def test_new_argumentless(self, parse_line):
        """NEW without argument parses correctly (§8.2.14)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW abbreviated")
    def test_new_abbreviated(self, parse_line):
        """N abbreviation parses correctly (§8.2.14)."""
        pytest.fail("Stub - implement test")
