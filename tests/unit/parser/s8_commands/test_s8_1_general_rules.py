"""Tests for General Command Rules parsing (§8.1).

Tests verify the textX grammar correctly captures general command syntax rules.

Reference: MUMPS 1995 ANSI Standard, Section 8.1
"""

import pytest


@pytest.mark.parser
class TestGeneralCommandRulesParsing:
    """Parser-level tests for General Command Rules (§8.1).

    Covers command spaces, comments, postconditions, timeouts, and abbreviations.
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: command spacing")
    def test_command_spacing(self, parse_line):
        """Command with proper spacing parses correctly (§8.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: command comment")
    def test_command_comment(self, parse_line):
        """Command followed by comment ; parses correctly (§8.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: command postcondition")
    def test_command_postcondition(self, parse_line):
        """Command with postcondition CMD:condition arg parses correctly (§8.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: argument postcondition")
    def test_argument_postcondition(self, parse_line):
        """Argument with postcondition CMD arg:condition parses correctly (§8.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: command timeout")
    def test_command_timeout(self, parse_line):
        """Command with timeout CMD:timeout arg parses correctly (§8.1)."""
        pytest.fail("Stub - implement test")


@pytest.mark.parser
class TestCommandAbbreviations:
    """Tests for command abbreviations (§8.1).

    Abbreviated forms (S, W, R) must parse identically to full forms (SET, WRITE, READ).
    Per FR-009: abbreviation parity tests.
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: SET abbreviation parity")
    def test_set_abbreviation_parity(self, parse_line):
        """S X=1 and SET X=1 produce identical ASG structure (§8.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: WRITE abbreviation parity")
    def test_write_abbreviation_parity(self, parse_line):
        """W X and WRITE X produce identical ASG structure (§8.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ abbreviation parity")
    def test_read_abbreviation_parity(self, parse_line):
        """R X and READ X produce identical ASG structure (§8.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: IF abbreviation parity")
    def test_if_abbreviation_parity(self, parse_line):
        """I cond and IF cond produce identical ASG structure (§8.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR abbreviation parity")
    def test_for_abbreviation_parity(self, parse_line):
        """F i=1:1:10 and FOR i=1:1:10 produce identical ASG structure (§8.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO abbreviation parity")
    def test_do_abbreviation_parity(self, parse_line):
        """D label and DO label produce identical ASG structure (§8.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: QUIT abbreviation parity")
    def test_quit_abbreviation_parity(self, parse_line):
        """Q and QUIT produce identical ASG structure (§8.1)."""
        pytest.fail("Stub - implement test")
