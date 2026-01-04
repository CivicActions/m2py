"""Tests for Expression Values parsing (§7.1.1).

Tests verify the textX grammar correctly captures expression value syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.1.1
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
class TestValuesParsing:
    """Parser-level tests for Expression Values (§7.1.1).

    Values are the basic units of expressions: literals, variables, functions.
    """

    def test_numeric_value(self, expr_metamodel):
        """Numeric value parses correctly (§7.1.1)."""
        model = expr_metamodel.model_from_str("42", "Expr")
        assert model is not None
        # Navigate to the NumericLiteral
        operand = model.left.operand
        assert operand.__class__.__name__ == "NumericLiteral"
        assert operand.value == 42

    def test_string_value(self, expr_metamodel):
        """String value parses correctly (§7.1.1)."""
        model = expr_metamodel.model_from_str('"hello"', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "StringLiteral"
        assert operand.value == "hello"

    def test_variable_as_value(self, expr_metamodel):
        """Variable reference as value parses correctly (§7.1.1)."""
        model = expr_metamodel.model_from_str("X", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "LocalVariable"
        assert operand.name == "X"

    def test_function_as_value(self, expr_metamodel):
        """Function call as value parses correctly (§7.1.1)."""
        model = expr_metamodel.model_from_str("$LENGTH(X)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        # Function name is stored without $ prefix
        assert operand.name == "LENGTH"
