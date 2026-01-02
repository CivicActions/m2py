"""Tests for READ command parsing (§8.2.17).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.17
"""

import pytest


@pytest.mark.parser
class TestReadCommandParsing:
    """Parser-level tests for READ command (§8.2.17)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ basic form")
    def test_read_basic(self, parse_line):
        """READ X parses correctly (§8.2.17)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ with prompt")
    def test_read_with_prompt(self, parse_line):
        """READ \"prompt\",X parses correctly (§8.2.17)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ with fixed length")
    def test_read_fixed_length(self, parse_line):
        """READ X#5 fixed length parses correctly (§8.2.17)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ with timeout")
    def test_read_with_timeout(self, parse_line):
        """READ X:timeout parses correctly (§8.2.17)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ single character")
    def test_read_single_char(self, parse_line):
        """READ *X single character parses correctly (§8.2.17)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ format control")
    def test_read_format_control(self, parse_line):
        """READ !,?10,# format controls parse correctly (§8.2.17)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ multiple targets")
    def test_read_multiple_targets(self, parse_line):
        """READ X,Y,Z multiple targets parses correctly (§8.2.17)."""
        pytest.fail("Stub - implement test")
