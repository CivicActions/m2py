"""Tests for semantic analyzer internal utilities.

Tests for internal functions of the semantic analyzer that don't fit
into spec-based categories.

Migrated from: tests/unit/test_semantic_analyzer.py::TestUnwrapExpression
"""

import pytest
from tests.helpers.parsing import parse_expression
from m2py.analysis.semantic_analyzer import unwrap_expression
from m2py.asg.expressions import MLiteral, MVariable


@pytest.mark.asg
class TestUnwrapExpression:
    """Test unwrap_expression function.

    Migrated from: TestUnwrapExpression
    """

    def test_unwrap_already_mexpr(self):
        """Unwrapping already an MExpr returns same object."""
        literal = MLiteral(value=42)
        result = unwrap_expression(literal)
        assert result is literal

    def test_unwrap_none(self):
        """Unwrapping None returns None."""
        result = unwrap_expression(None)
        assert result is None

    def test_unwrap_textx_expr(self):
        """Unwrapping textX Expr produces proper ASG node."""
        expr = parse_expression("X")
        result = unwrap_expression(expr)

        # Should be unwrapped to the LocalVariable custom class
        assert isinstance(result, MVariable)
        assert result.name == "X"
