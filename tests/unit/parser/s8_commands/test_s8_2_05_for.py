"""Tests for FOR command parsing (§8.2.5).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.5
"""

import pytest


@pytest.mark.parser
class TestForCommandParsing:
    """Parser-level tests for FOR command (§8.2.5)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR bounded loop")
    def test_for_bounded(self, parse_line):
        """FOR i=1:1:10 bounded loop parses correctly (§8.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR string list")
    def test_for_string_list(self, parse_line):
        """FOR i=\"a\",\"b\",\"c\" string list parses correctly (§8.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR open-ended")
    def test_for_open_ended(self, parse_line):
        """FOR i=1:1 open-ended loop parses correctly (§8.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR argumentless")
    def test_for_argumentless(self, parse_line):
        """FOR without argument parses correctly (§8.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR with mixed forms")
    def test_for_mixed_forms(self, parse_line):
        """FOR i=1:1:5,10,20:5:50 mixed forms parse correctly (§8.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR with negative increment")
    def test_for_negative_increment(self, parse_line):
        """FOR i=10:-1:1 negative increment parses correctly (§8.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR with decimal increment")
    def test_for_decimal_increment(self, parse_line):
        """FOR i=0:.5:5 decimal increment parses correctly (§8.2.5)."""
        pytest.fail("Stub - implement test")
