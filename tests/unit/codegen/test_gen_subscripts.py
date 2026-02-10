"""Tests for gen_subscripts_tuple() helper function.

Spec 020 (S-02): Subscript tuple extraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import MagicMock

import pytest

from m2py.codegen.statements import gen_subscripts_tuple

pytestmark = pytest.mark.codegen


# ---------------------------------------------------------------------------
# Minimal mock context — gen_subscripts_tuple only needs ctx for generate_expr
# calls, but when we pass pre-evaluated strings it doesn't use ctx at all.
# ---------------------------------------------------------------------------


@dataclass
class _MockContext:
    """Minimal mock of GeneratorContext for testing."""

    strategy: object = None
    uses_dynamic_locals: bool = False
    state_vars: set = field(default_factory=set)


# ---------------------------------------------------------------------------
# Pre-evaluated string tests (bypass generate_expr)
# ---------------------------------------------------------------------------


class TestGenSubscriptsTuplePreEvaluated:
    """Test gen_subscripts_tuple with pre-evaluated expression strings."""

    def test_empty_list_returns_empty_tuple(self):
        ctx = _MockContext()
        result = gen_subscripts_tuple([], ctx)
        assert result == "()"

    def test_single_element_has_trailing_comma(self):
        ctx = _MockContext()
        result = gen_subscripts_tuple(["42"], ctx)
        assert result == "(42,)"

    def test_two_elements_have_trailing_comma(self):
        ctx = _MockContext()
        result = gen_subscripts_tuple(["42", '"hello"'], ctx)
        assert result == '(42, "hello",)'

    def test_three_elements(self):
        ctx = _MockContext()
        result = gen_subscripts_tuple(["a", "b", "c"], ctx)
        assert result == "(a, b, c,)"

    def test_complex_expressions(self):
        ctx = _MockContext()
        result = gen_subscripts_tuple(
            ["m_str(x)", 'state._locals.get("Y", MArray())'], ctx
        )
        assert result == '(m_str(x), state._locals.get("Y", MArray()),)'

    def test_custom_empty_sentinel(self):
        ctx = _MockContext()
        result = gen_subscripts_tuple([], ctx, empty='("",)')
        assert result == '("",)'

    def test_str_wrap_with_pre_evaluated(self):
        ctx = _MockContext()
        result = gen_subscripts_tuple(["x", "y"], ctx, str_wrap=True)
        assert result == "(str(x), str(y),)"

    def test_str_wrap_single_element(self):
        ctx = _MockContext()
        result = gen_subscripts_tuple(["expr1"], ctx, str_wrap=True)
        assert result == "(str(expr1),)"


# ---------------------------------------------------------------------------
# ASG node tests (with mocked generate_expr)
# ---------------------------------------------------------------------------


class TestGenSubscriptsTupleASGNodes:
    """Test gen_subscripts_tuple with ASG expression nodes.

    These tests use mock ASG nodes to verify that generate_expr is called
    correctly and the results are formatted into tuple strings.
    """

    def test_single_asg_node(self, monkeypatch):
        """Single ASG subscript node produces (expr,) tuple."""
        node = MagicMock()
        ctx = _MockContext()

        # Mock generate_expr to return a known string
        import m2py.codegen.statements as stmts_mod

        monkeypatch.setattr(stmts_mod, "generate_expr", lambda sub, c, **kw: "42")

        result = gen_subscripts_tuple([node], ctx)
        assert result == "(42,)"

    def test_multiple_asg_nodes(self, monkeypatch):
        """Multiple ASG subscript nodes produce (expr1, expr2,) tuple."""
        nodes = [MagicMock(), MagicMock()]
        ctx = _MockContext()

        call_count = [0]

        def mock_gen(sub, c, **kw):
            call_count[0] += 1
            return f"expr{call_count[0]}"

        import m2py.codegen.statements as stmts_mod

        monkeypatch.setattr(stmts_mod, "generate_expr", mock_gen)

        result = gen_subscripts_tuple(nodes, ctx)
        assert result == "(expr1, expr2,)"

    def test_subscript_context_forwarded(self, monkeypatch):
        """subscript_context=True is passed through to generate_expr."""
        node = MagicMock()
        ctx = _MockContext()
        captured_kwargs = {}

        def mock_gen(sub, c, **kw):
            captured_kwargs.update(kw)
            return "val"

        import m2py.codegen.statements as stmts_mod

        monkeypatch.setattr(stmts_mod, "generate_expr", mock_gen)

        gen_subscripts_tuple([node], ctx, subscript_context=True)
        assert captured_kwargs.get("subscript_context") is True

    def test_str_wrap_with_asg_nodes(self, monkeypatch):
        """str_wrap=True wraps generate_expr output in str()."""
        nodes = [MagicMock(), MagicMock()]
        ctx = _MockContext()

        call_count = [0]

        def mock_gen(sub, c, **kw):
            call_count[0] += 1
            return f"expr{call_count[0]}"

        import m2py.codegen.statements as stmts_mod

        monkeypatch.setattr(stmts_mod, "generate_expr", mock_gen)

        result = gen_subscripts_tuple(nodes, ctx, str_wrap=True)
        assert result == "(str(expr1), str(expr2),)"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestGenSubscriptsTupleEdgeCases:
    """Edge case tests for gen_subscripts_tuple."""

    def test_none_like_empty(self):
        """Empty list returns the empty sentinel."""
        ctx = _MockContext()
        assert gen_subscripts_tuple([], ctx) == "()"

    def test_single_empty_string_expression(self):
        """A single empty-string expression still produces a tuple."""
        ctx = _MockContext()
        result = gen_subscripts_tuple(['""'], ctx)
        assert result == '("",)'

    def test_expression_with_parens(self):
        """Subscript expressions can contain parentheses."""
        ctx = _MockContext()
        result = gen_subscripts_tuple(["f(x)", "g(y, z)"], ctx)
        assert result == "(f(x), g(y, z),)"
