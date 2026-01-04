"""Tests for Literal parsing (§7.1.4).

Tests verify the textX grammar correctly captures literal syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.1.4
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_expression_classes


@pytest.fixture(scope="module")
def expr_metamodel():
    """Load the expression grammar metamodel with custom classes."""
    grammar_path = (
        Path(__file__).parent.parent.parent.parent.parent
        / "src"
        / "m2py"
        / "grammar"
        / "expressions.tx"
    )
    return metamodel_from_file(
        str(grammar_path), classes=get_expression_classes(), skipws=True
    )


@pytest.mark.parser
class TestNumericLiterals:
    """Test numeric literal parsing (§7.1.4)."""

    def test_integer_literal(self, expr_metamodel):
        """Integer literal 42 parses correctly (§7.1.4)."""
        model = expr_metamodel.model_from_str("42", "Expr")
        assert model is not None

    def test_decimal_literal(self, expr_metamodel):
        """Decimal literal 3.14 parses correctly (§7.1.4)."""
        model = expr_metamodel.model_from_str("3.14", "Expr")
        assert model is not None

    def test_negative_integer(self, expr_metamodel):
        """Negative integer -42 (unary minus) parses correctly (§7.1.4)."""
        model = expr_metamodel.model_from_str("-42", "Expr")
        assert model is not None


@pytest.mark.parser
class TestStringLiterals:
    """Test string literal parsing (§7.1.4)."""

    def test_string_literal(self, expr_metamodel):
        """Simple quoted string parses correctly (§7.1.4)."""
        model = expr_metamodel.model_from_str('"hello"', "Expr")
        assert model is not None

    def test_empty_string(self, expr_metamodel):
        """Empty string \"\" parses correctly (§7.1.4)."""
        model = expr_metamodel.model_from_str('""', "Expr")
        assert model is not None

    def test_string_embedded_quotes(self, expr_metamodel):
        """String with embedded quotes parses correctly (§7.1.4)."""
        model = expr_metamodel.model_from_str('"say ""hi"""', "Expr")
        assert model is not None

    def test_exponential_literal(self, expr_metamodel):
        """Exponential literal 1.23E5 parses correctly (§7.1.4)."""
        model = expr_metamodel.model_from_str("1.23E5", "Expr")
        assert model is not None
        # Navigate to the NumericLiteral
        operand = model.left.operand
        assert operand.__class__.__name__ == "NumericLiteral"
        # 1.23E5 = 123000.0
        assert operand.value == 123000.0
