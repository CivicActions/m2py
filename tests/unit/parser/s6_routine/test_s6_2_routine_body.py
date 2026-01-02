"""Tests for Routine Body parsing (§6.2).

Tests verify the textX grammar correctly captures routine body structure,
including level lines, formal lines, labels, and line body.

Reference: MUMPS 1995 ANSI Standard, Sections 6.2.1-6.2.5
"""

import pytest


@pytest.mark.parser
class TestRoutineBodyParsing:
    """Parser-level tests for Routine Body (§6.2).

    Covers:
    - §6.2.1 Level Line
    - §6.2.2 Formal Line
    - §6.2.3 Label
    - §6.2.4 Label Separator
    - §6.2.5 Line Body
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: level line parsing")
    def test_level_line_parsing(self, parse_mumps):
        """Level line with proper dot indentation parses correctly (§6.2.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: formal line parsing")
    def test_formal_line_parsing(self, parse_mumps):
        """Formal line with parameter list parses correctly (§6.2.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: label parsing")
    def test_label_parsing(self, parse_mumps):
        """Label on a line parses correctly (§6.2.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: label separator")
    def test_label_separator(self, parse_mumps):
        """Label separator (space or tab) parses correctly (§6.2.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: line body parsing")
    def test_line_body_parsing(self, parse_mumps):
        """Line body with commands parses correctly (§6.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: multiple commands on line")
    def test_multiple_commands_on_line(self, parse_mumps):
        """Multiple commands separated by spaces parse correctly (§6.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: comment after commands")
    def test_comment_after_commands(self, parse_mumps):
        """Comment (;) after commands parses correctly (§6.2.5)."""
        pytest.fail("Stub - implement test")
