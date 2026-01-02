"""Tests for Literal parsing (§7.1.4).

Tests verify the textX grammar correctly captures literal syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.1.4
"""

import pytest


@pytest.mark.parser
class TestLiteralsParsing:
    """Parser-level tests for Literals (§7.1.4).

    Literal types: numeric (integer, decimal, exponential) and string.
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: integer literal")
    def test_integer_literal(self, parse_expression):
        """Integer literal 123 parses correctly (§7.1.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: decimal literal")
    def test_decimal_literal(self, parse_expression):
        """Decimal literal 123.456 parses correctly (§7.1.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: exponential literal")
    def test_exponential_literal(self, parse_expression):
        """Exponential literal 1.23E5 parses correctly (§7.1.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: negative number")
    def test_negative_number(self, parse_expression):
        """Negative number -123 parses correctly (§7.1.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: string literal")
    def test_string_literal(self, parse_expression):
        """String literal \"hello\" parses correctly (§7.1.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: string with embedded quotes")
    def test_string_embedded_quotes(self, parse_expression):
        """String with embedded quotes \"he said \"\"hi\"\"\" parses correctly (§7.1.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: empty string")
    def test_empty_string(self, parse_expression):
        """Empty string \"\" parses correctly (§7.1.4)."""
        pytest.fail("Stub - implement test")
