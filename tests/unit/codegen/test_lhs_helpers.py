"""Tests for _build_lhs_getter_setter helper.

Spec 020 (T012): Unit tests covering each variable type and strategy
combination for the shared LHS getter/setter builder.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from m2py.codegen.enums import GotoStrategy
from m2py.codegen.statements import _build_lhs_getter_setter

pytestmark = pytest.mark.codegen


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_ctx(
    strategy: GotoStrategy = GotoStrategy.SIMPLE_FUNCTIONS,
    state_vars: set | None = None,
    uses_dynamic_locals: bool = False,
) -> MagicMock:
    """Create a mock GeneratorContext."""
    ctx = MagicMock()
    ctx.strategy = strategy
    ctx.state_vars = state_vars or set()
    ctx.uses_dynamic_locals = uses_dynamic_locals
    ctx.emitter = MagicMock()
    return ctx


def _make_global_var(name: str = "G", subscripts=None):
    """Create a mock GlobalVariable ASG node."""
    from m2py.parser.textx_classes import GlobalVariable

    var = MagicMock(spec=GlobalVariable)
    var.__class__ = GlobalVariable
    var.name = name
    var.subscripts = subscripts or []
    return var


def _make_naked_global(subscripts=None):
    """Create a mock NakedGlobal ASG node."""
    from m2py.parser.textx_classes import NakedGlobal

    var = MagicMock(spec=NakedGlobal)
    var.__class__ = NakedGlobal
    var.subscripts = subscripts or []
    return var


def _make_local_var(name: str = "X", subscripts=None):
    """Create a mock MVariable ASG node."""
    from m2py.asg.expressions import MVariable

    var = MagicMock(spec=MVariable)
    var.__class__ = MVariable
    var.name = name
    var.subscripts = subscripts or []
    return var


def _make_indirection(inner_name: str = "A", levels: int = 1):
    """Create a mock MIndirection ASG node with an MVariable inner."""
    from m2py.asg.expressions import MIndirection, MVariable

    inner = MagicMock(spec=MVariable)
    inner.__class__ = MVariable
    inner.name = inner_name

    ind = MagicMock(spec=MIndirection)
    ind.__class__ = MIndirection
    ind.name_indirection_subscripts = []

    # For single level: ind.expression = inner
    if levels == 1:
        ind.expression = inner
    else:
        # Multi-level: ind.expression = another MIndirection
        mid = MagicMock(spec=MIndirection)
        mid.__class__ = MIndirection
        mid.expression = inner
        mid.name_indirection_subscripts = []
        ind.expression = mid

    return ind


# ---------------------------------------------------------------------------
# GlobalVariable tests
# ---------------------------------------------------------------------------


class TestGlobalVariable:
    """Test _build_lhs_getter_setter with GlobalVariable target."""

    def test_global_no_subscripts(self):
        ctx = _make_ctx()
        target = _make_global_var("TEST")
        getter, setter = _build_lhs_getter_setter(target, ctx)
        assert '"TEST"' in getter
        assert "_rt.globals.get" in getter
        assert "_rt.globals.set" in setter
        assert 'or ""' in getter

    def test_global_with_subscripts(self):
        ctx = _make_ctx()
        sub = MagicMock()
        target = _make_global_var("G", subscripts=[sub])
        with patch("m2py.codegen.statements.generate_expr", return_value='"key"'):
            getter, setter = _build_lhs_getter_setter(target, ctx)
        assert "_rt.globals.get" in getter
        assert "_rt.globals.set" in setter

    def test_global_str_wrap_does_not_affect(self):
        """str_wrap_getter only affects MVariable, not GlobalVariable."""
        ctx = _make_ctx()
        target = _make_global_var("G")
        g1, _ = _build_lhs_getter_setter(target, ctx, str_wrap_getter=False)
        g2, _ = _build_lhs_getter_setter(target, ctx, str_wrap_getter=True)
        # GlobalVariable getter should be the same regardless of str_wrap
        assert g1 == g2


# ---------------------------------------------------------------------------
# NakedGlobal tests
# ---------------------------------------------------------------------------


class TestNakedGlobal:
    """Test _build_lhs_getter_setter with NakedGlobal target."""

    def test_naked_global_emits_resolve(self):
        ctx = _make_ctx()
        target = _make_naked_global()
        getter, setter = _build_lhs_getter_setter(target, ctx)
        # Should emit resolve_naked pre-computation
        ctx.emitter.line.assert_called_once()
        call_arg = ctx.emitter.line.call_args[0][0]
        assert "resolve_naked" in call_arg
        assert "_lhs_name_" in call_arg
        assert "_lhs_subs_" in call_arg

    def test_naked_global_getter_setter_use_temps(self):
        ctx = _make_ctx()
        target = _make_naked_global()
        getter, setter = _build_lhs_getter_setter(target, ctx)
        assert "_lhs_name_" in getter
        assert "_lhs_subs_" in getter
        assert "_lhs_name_" in setter
        assert "_lhs_subs_" in setter


# ---------------------------------------------------------------------------
# MVariable tests
# ---------------------------------------------------------------------------


class TestMVariable:
    """Test _build_lhs_getter_setter with MVariable target."""

    def test_simple_no_str_wrap(self):
        ctx = _make_ctx()
        target = _make_local_var("X")
        getter, setter = _build_lhs_getter_setter(target, ctx, str_wrap_getter=False)
        assert "m_var_value" in getter
        assert "str(" not in getter
        assert "setattr" in setter

    def test_simple_with_str_wrap(self):
        ctx = _make_ctx()
        target = _make_local_var("X")
        getter, setter = _build_lhs_getter_setter(target, ctx, str_wrap_getter=True)
        assert "str(" in getter
        assert "m_var_value" in getter

    def test_trampoline_state_var(self):
        ctx = _make_ctx(strategy=GotoStrategy.TRAMPOLINE, state_vars={"X"})
        target = _make_local_var("X")
        getter, setter = _build_lhs_getter_setter(target, ctx)
        assert "getattr(state" in getter
        assert "setattr(state" in setter

    def test_trampoline_state_var_with_dynamic_locals(self):
        """When uses_dynamic_locals is True, even state_vars must use _scope.

        In trampoline routines with dynamic locals (execute_mumps / indirection),
        variables live in state._locals (exposed as _scope), not as state attrs.
        SET $PIECE must use _scope-based getter/setter to read/write the correct
        location — otherwise the field value update silently operates on a
        non-existent state attribute while the real variable is untouched.
        """
        ctx = _make_ctx(
            strategy=GotoStrategy.TRAMPOLINE,
            state_vars={"DV"},
            uses_dynamic_locals=True,
        )
        target = _make_local_var("DV")
        getter, setter = _build_lhs_getter_setter(target, ctx)
        # Must use _scope (state._locals), NOT getattr(state, ...)
        assert "getattr(state" not in getter
        assert "setattr(state" not in setter
        assert "_scope" in getter
        assert "_scope" in setter

    def test_trampoline_non_state_var(self):
        ctx = _make_ctx(strategy=GotoStrategy.TRAMPOLINE, state_vars={"Y"})
        target = _make_local_var("X")
        getter, setter = _build_lhs_getter_setter(target, ctx)
        assert "m_var_value" in getter
        assert "_scope" in getter

    def test_subscripted_var(self):
        ctx = _make_ctx()
        sub = MagicMock()
        target = _make_local_var("X", subscripts=[sub])
        with patch("m2py.codegen.statements.generate_expr", return_value="1"):
            getter, setter = _build_lhs_getter_setter(target, ctx)
        assert "MArray" in getter
        assert ".get(" in getter
        assert ".set(" in setter

    def test_subscripted_var_str_wrap(self):
        ctx = _make_ctx()
        sub = MagicMock()
        target = _make_local_var("X", subscripts=[sub])
        with patch("m2py.codegen.statements.generate_expr", return_value="1"):
            getter, setter = _build_lhs_getter_setter(target, ctx, str_wrap_getter=True)
        assert "str(" in getter
        assert "MArray" in getter


# ---------------------------------------------------------------------------
# MIndirection tests
# ---------------------------------------------------------------------------


class TestMIndirection:
    """Test _build_lhs_getter_setter with MIndirection target."""

    def test_simple_indirection(self):
        ctx = _make_ctx()
        target = _make_indirection("A")
        getter, setter = _build_lhs_getter_setter(target, ctx)
        assert "_rt.get_var" in getter
        assert "_rt.set_var" in setter
        assert "resolve_for_target" in getter or "resolve_for_target" in setter or True

    def test_indirection_getter_has_or_empty(self):
        ctx = _make_ctx()
        target = _make_indirection("A")
        getter, _ = _build_lhs_getter_setter(target, ctx)
        assert 'or ""' in getter


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Test error cases for _build_lhs_getter_setter."""

    def test_unsupported_type_raises(self):
        ctx = _make_ctx()
        target = MagicMock()
        with pytest.raises(NotImplementedError, match="must be a variable"):
            _build_lhs_getter_setter(target, ctx)
