"""Tests for Literal parsing (§7.1.4).

Tests verify the textX grammar correctly captures literal syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.1.4

Migrated from: tests/unit/test_expression_grammar.py (TestNumericLiterals, TestStringLiterals)
"""

import pytest


@pytest.mark.parser
class TestNumericLiterals:
    """Test numeric literal parsing (§7.1.4).

    Migrated from: tests/unit/test_expression_grammar.py::TestNumericLiterals
    """

    def test_integer(self, parse_expression):
        """Parse integer literal (§7.1.4)."""
        model = parse_expression("42")
        assert model is not None

    def test_decimal(self, parse_expression):
        """Parse decimal literal (§7.1.4)."""
        model = parse_expression("3.14")
        assert model is not None

    def test_negative_integer(self, parse_expression):
        """Parse negative integer (unary minus) (§7.1.4)."""
        model = parse_expression("-42")
        assert model is not None


@pytest.mark.parser
class TestStringLiterals:
    """Test string literal parsing (§7.1.4).

    Migrated from: tests/unit/test_expression_grammar.py::TestStringLiterals
    """

    def test_simple_string(self, parse_expression):
        """Parse simple quoted string (§7.1.4)."""
        model = parse_expression('"hello"')
        assert model is not None

    def test_empty_string(self, parse_expression):
        """Parse empty string (§7.1.4)."""
        model = parse_expression('""')
        assert model is not None

    def test_escaped_quote(self, parse_expression):
        """Parse string with escaped quote (§7.1.4)."""
        model = parse_expression('"say ""hi"""')
        assert model is not None
