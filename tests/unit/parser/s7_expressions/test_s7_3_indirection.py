"""Tests for Indirection parsing (§7.3).

Tests verify the textX grammar correctly captures indirection syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.3
"""

import pytest


@pytest.mark.parser
class TestIndirectionParsing:
    """Parser-level tests for Indirection (§7.3).

    Types of indirection: name, argument, pattern.
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: name indirection")
    def test_name_indirection(self, parse_expression):
        """Name indirection @var parses correctly (§7.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: subscript indirection")
    def test_subscript_indirection(self, parse_expression):
        """Subscript indirection @var@(sub) parses correctly (§7.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: argument indirection")
    def test_argument_indirection(self, parse_line):
        """Argument indirection S @arg parses correctly (§7.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: pattern indirection")
    def test_pattern_indirection(self, parse_expression):
        """Pattern indirection X?@pattern parses correctly (§7.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: nested indirection")
    def test_nested_indirection(self, parse_expression):
        """Nested indirection @@var parses correctly (§7.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: indirection in SET target")
    def test_indirection_in_set_target(self, parse_line):
        """Indirection in SET target S @var=1 parses correctly (§7.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: indirection in DO")
    def test_indirection_in_do(self, parse_line):
        """Indirection in DO argument D @routine parses correctly (§7.3)."""
        pytest.fail("Stub - implement test")
