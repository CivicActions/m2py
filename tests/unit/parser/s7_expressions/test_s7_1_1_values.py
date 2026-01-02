"""Tests for Expression Values parsing (§7.1.1).

Tests verify the textX grammar correctly captures expression value syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.1.1

Migrated from:
- tests/unit/test_line_parser.py::TestParseExpression
"""

import pytest

from tests.helpers.parsing import parse_expression


@pytest.mark.parser
class TestValuesParsing:
    """Parser-level tests for Expression Values (§7.1.1).

    Values are the basic units of expressions: literals, variables, functions.
    """

    def test_numeric_value(self, expr_metamodel):
        """Numeric value parses correctly (§7.1.1)."""
        model = expr_metamodel.model_from_str("42", "Expr")
        assert model is not None

    def test_string_value(self, expr_metamodel):
        """String value parses correctly (§7.1.1)."""
        model = expr_metamodel.model_from_str('"hello"', "Expr")
        assert model is not None

    def test_variable_as_value(self, expr_metamodel):
        """Variable reference as value parses correctly (§7.1.1)."""
        model = expr_metamodel.model_from_str("X", "Expr")
        assert model is not None

    def test_function_as_value(self, expr_metamodel):
        """Function call as value parses correctly (§7.1.1)."""
        model = expr_metamodel.model_from_str("$LENGTH(X)", "Expr")
        assert model is not None


@pytest.mark.parser
class TestParentheses:
    """Tests for parenthesized expressions (§7.1.1).

    Parentheses control evaluation order in expressions.

    Migrated from test_expression_grammar.py::TestParentheses.
    """

    def test_simple_parens(self, expr_metamodel):
        """Parse (expr) - simple parenthesized expression (§7.1.1)."""
        model = expr_metamodel.model_from_str("(X+Y)", "Expr")
        assert model is not None

    def test_nested_parens(self, expr_metamodel):
        """Parse nested parentheses (§7.1.1)."""
        model = expr_metamodel.model_from_str("((X+Y)*Z)", "Expr")
        assert model is not None


@pytest.mark.parser
class TestComplexExpressions:
    """Tests for complex expression parsing (§7.1.1).

    Verifies the parser handles combinations of values,
    operators, and function calls correctly.

    Migrated from test_expression_grammar.py::TestComplexExpressions.
    """

    def test_complex_arithmetic(self, expr_metamodel):
        """Parse complex arithmetic expression (§7.1.1)."""
        model = expr_metamodel.model_from_str("A+B*C-D/E", "Expr")
        assert model is not None

    def test_function_in_expression(self, expr_metamodel):
        """Parse function call within expression (§7.1.1)."""
        model = expr_metamodel.model_from_str("$LENGTH(X)+1", "Expr")
        assert model is not None

    def test_subscripted_in_expression(self, expr_metamodel):
        """Parse subscripted variable in expression (§7.1.1)."""
        model = expr_metamodel.model_from_str("A(I)+B(J)", "Expr")
        assert model is not None


@pytest.mark.parser
class TestParseExpression:
    """Test expression parsing.

    Migrated from: tests/unit/test_line_parser.py::TestParseExpression
    """

    def test_parse_simple_var(self):
        """Variable X parses correctly."""
        result = parse_expression("X")
        assert result is not None
        # The parsed expression is an Expr with structure
        assert hasattr(result, "left")

    def test_parse_arithmetic(self):
        """X+Y*Z parses with binary operators."""
        result = parse_expression("X+Y*Z")
        assert result is not None
        # Has left operand and tail for operators
        assert result.left is not None
        assert len(result.tail) > 0

    def test_parse_function(self):
        """$LENGTH(X) parses correctly."""
        result = parse_expression("$LENGTH(X)")
        assert result is not None
        # Function call is wrapped in expression structure
        assert hasattr(result, "left")

    def test_parse_global_var(self):
        """^GLOBAL parses correctly."""
        result = parse_expression("^GLOBAL")
        assert result is not None
        assert hasattr(result, "left")

    def test_parse_special_var(self):
        """$TEST parses correctly."""
        result = parse_expression("$TEST")
        assert result is not None
        assert hasattr(result, "left")
