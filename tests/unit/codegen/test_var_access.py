"""Unit tests for codegen/var_access.py helpers.

Spec 020 Phase 8 (T032): Tests var_read_expr, var_write_stmt,
var_base_expr, and scope_dict_expr across all 3 strategies.
"""

from unittest.mock import MagicMock

import pytest

from m2py.codegen.enums import GotoStrategy
from m2py.codegen.var_access import (
    scope_dict_expr,
    var_base_expr,
    var_read_expr,
    var_write_stmt,
)


def _make_ctx(strategy, uses_dynamic_locals=False, state_vars=None):
    """Build a minimal mock GeneratorContext."""
    ctx = MagicMock()
    ctx.strategy = strategy
    ctx.uses_dynamic_locals = uses_dynamic_locals
    ctx.state_vars = state_vars or set()
    ctx.array_vars = state_vars or set()
    return ctx


# ── SIMPLE_FUNCTIONS strategy ────────────────────────────────────────


@pytest.mark.codegen
class TestSimpleFunctions:
    """Tests for SIMPLE_FUNCTIONS strategy (variables in _scope)."""

    @pytest.fixture()
    def ctx(self):
        return _make_ctx(GotoStrategy.SIMPLE_FUNCTIONS)

    def test_read_simple(self, ctx):
        assert var_read_expr("X", ctx) == "m_var_value(_scope['X'])"

    def test_read_percent_var(self, ctx):
        result = var_read_expr("%FOO", ctx)
        assert "_scope['_pct_FOO']" in result

    def test_write_simple(self, ctx):
        result = var_write_stmt("X", "42", ctx)
        assert result == "_scope.setdefault('X', MArray()).value = 42"

    def test_base_read(self, ctx):
        assert var_base_expr("X", ctx) == "_scope.get('X', MArray())"

    def test_base_write(self, ctx):
        assert (
            var_base_expr("X", ctx, for_write=True)
            == "_scope.setdefault('X', MArray())"
        )

    def test_scope_dict(self, ctx):
        assert scope_dict_expr(ctx) == "_scope"


# ── TRAMPOLINE + dynamic locals ─────────────────────────────────────


@pytest.mark.codegen
class TestTrampolineDynamic:
    """Tests for TRAMPOLINE with dynamic locals (state._locals dict)."""

    @pytest.fixture()
    def ctx(self):
        return _make_ctx(GotoStrategy.TRAMPOLINE, uses_dynamic_locals=True)

    def test_read_simple(self, ctx):
        assert var_read_expr("X", ctx) == "m_var_value(state._locals['X'])"

    def test_write_simple(self, ctx):
        result = var_write_stmt("X", "42", ctx)
        assert result == "state._locals.setdefault('X', MArray()).value = 42"

    def test_base_read(self, ctx):
        assert var_base_expr("X", ctx) == "state._locals.get('X', MArray())"

    def test_base_write(self, ctx):
        assert (
            var_base_expr("X", ctx, for_write=True)
            == "state._locals.setdefault('X', MArray())"
        )

    def test_scope_dict(self, ctx):
        assert scope_dict_expr(ctx) == "state._locals"


# ── TRAMPOLINE + static state vars ──────────────────────────────────


@pytest.mark.codegen
class TestTrampolineStatic:
    """Tests for TRAMPOLINE with static state vars (state.field)."""

    @pytest.fixture()
    def ctx(self):
        return _make_ctx(
            GotoStrategy.TRAMPOLINE,
            uses_dynamic_locals=False,
            state_vars={"X", "Y"},
        )

    def test_read_simple(self, ctx):
        assert var_read_expr("X", ctx) == "state.X"

    def test_write_simple(self, ctx):
        assert var_write_stmt("X", "42", ctx) == "state.X = 42"

    def test_base(self, ctx):
        # Static vars: state.X is already the MArray
        assert var_base_expr("X", ctx) == "state.X"
        assert var_base_expr("X", ctx, for_write=True) == "state.X"

    def test_unknown_var_falls_through_to_scope(self, ctx):
        """Vars not in state_vars use _scope even in TRAMPOLINE."""
        assert var_read_expr("Z", ctx) == "m_var_value(_scope['Z'])"

    def test_scope_dict(self, ctx):
        assert scope_dict_expr(ctx) == "_scope"
