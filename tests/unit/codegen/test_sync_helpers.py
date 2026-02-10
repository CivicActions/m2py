"""Tests for emit_state_to_scope_sync and emit_scope_to_state_sync helpers.

Spec 020 (T017): Unit tests covering dynamic_locals=True/False
and both sync directions.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from m2py.codegen.statements import (
    emit_scope_to_state_sync,
    emit_state_to_scope_sync,
)

pytestmark = pytest.mark.codegen


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_ctx(uses_dynamic_locals: bool = True) -> MagicMock:
    """Create a mock GeneratorContext with a recording emitter."""
    ctx = MagicMock()
    ctx.uses_dynamic_locals = uses_dynamic_locals

    # Track indentation context manager
    indent_cm = MagicMock()
    ctx.emitter.indented.return_value = indent_cm
    indent_cm.__enter__ = MagicMock(return_value=None)
    indent_cm.__exit__ = MagicMock(return_value=False)

    return ctx


# ---------------------------------------------------------------------------
# emit_state_to_scope_sync tests
# ---------------------------------------------------------------------------


class TestEmitStateToScopeSync:
    """Test state._locals → _scope sync helper."""

    def test_emits_update_when_dynamic(self):
        ctx = _make_ctx(uses_dynamic_locals=True)
        emit_state_to_scope_sync(ctx)
        ctx.emitter.line.assert_called_once()
        emitted = ctx.emitter.line.call_args[0][0]
        assert "_scope.update" in emitted
        assert "state._locals.items()" in emitted

    def test_noop_when_not_dynamic(self):
        ctx = _make_ctx(uses_dynamic_locals=False)
        emit_state_to_scope_sync(ctx)
        ctx.emitter.line.assert_not_called()


# ---------------------------------------------------------------------------
# emit_scope_to_state_sync tests
# ---------------------------------------------------------------------------


class TestEmitScopeToStateSync:
    """Test _scope → state._locals sync helper."""

    def test_emits_marray_wrapping_loop_when_dynamic(self):
        ctx = _make_ctx(uses_dynamic_locals=True)
        emit_scope_to_state_sync(ctx)
        # Should emit multiple lines (for loop, isinstance check, MArray wrapping)
        assert ctx.emitter.line.call_count >= 5
        all_lines = [c[0][0] for c in ctx.emitter.line.call_args_list]
        assert any("for _k, _v in _scope.items():" in line for line in all_lines)
        assert any("isinstance(_v, MArray)" in line for line in all_lines)
        assert any("state._locals[_k] = _v" in line for line in all_lines)
        assert any("_m = MArray()" in line for line in all_lines)
        assert any("_m.value = _v" in line for line in all_lines)
        assert any("state._locals[_k] = _m" in line for line in all_lines)

    def test_noop_when_not_dynamic(self):
        ctx = _make_ctx(uses_dynamic_locals=False)
        emit_scope_to_state_sync(ctx)
        ctx.emitter.line.assert_not_called()

    def test_uses_indented_context(self):
        ctx = _make_ctx(uses_dynamic_locals=True)
        emit_scope_to_state_sync(ctx)
        # Should use ctx.emitter.indented() for indentation
        assert ctx.emitter.indented.call_count >= 2


# ---------------------------------------------------------------------------
# Both directions in same block
# ---------------------------------------------------------------------------


class TestBothDirections:
    """Test both sync directions in sequence (e.g., pre/post call pattern)."""

    def test_pre_post_call_pattern(self):
        """Simulate the common pattern: state→scope before call, scope→state after."""
        ctx = _make_ctx(uses_dynamic_locals=True)

        # Pre-call: state → scope
        emit_state_to_scope_sync(ctx)
        pre_call_count = ctx.emitter.line.call_count

        # Post-call: scope → state
        emit_scope_to_state_sync(ctx)
        total_count = ctx.emitter.line.call_count

        # Should have emitted lines for both directions
        assert pre_call_count >= 1
        assert total_count > pre_call_count
