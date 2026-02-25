"""Tests for emit_state_var_to_scope() — state→scope sync (MArray wrapping).

Commit 0d64d04f introduced emit_state_var_to_scope() which wraps plain scalars
in MArray objects when syncing state attributes to _scope before DO calls.
Previously, bare scalars overwrote MArray objects in _scope, causing
AttributeError when called routines used _scope["X"].value.

Also tests the inverse direction emit_scope_var_to_state() codegen output
(commit c2234f8b) for completeness.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from m2py.codegen.emitter import CodeEmitter
from m2py.codegen.statements import emit_state_var_to_scope, emit_scope_var_to_state


# ---------------------------------------------------------------------------
# Minimal mock of GeneratorContext with only the fields these helpers use
# ---------------------------------------------------------------------------
@dataclass
class _MockCtx:
    emitter: CodeEmitter = field(default_factory=CodeEmitter)
    array_vars: set = field(default_factory=set)
    state_vars: set = field(default_factory=set)
    uses_dynamic_locals: bool = False


# =============================================================================
# emit_state_var_to_scope  (state→scope direction)
# =============================================================================


@pytest.mark.codegen
class TestEmitStateVarToScopeSimple:
    """Verify generated code for simple (non-array) variables."""

    def test_simple_var_wraps_in_marray(self):
        """Simple var produces MArray wrapping logic, not direct assignment."""
        ctx = _MockCtx(array_vars=set())
        emit_state_var_to_scope(ctx, "X", "X")
        code = ctx.emitter.get_code()

        # Should check for existing MArray
        assert "_scope.get('X')" in code
        assert "isinstance(_m, MArray)" in code
        # Should create MArray if needed
        assert "_m = MArray()" in code
        # Should set value on MArray
        assert "_m.value = state.X" in code

    def test_simple_var_reuses_existing_marray(self):
        """Generated code reuses existing MArray from _scope if present."""
        ctx = _MockCtx(array_vars=set())
        emit_state_var_to_scope(ctx, "U", "U")
        code = ctx.emitter.get_code()

        # The conditional: only create new MArray if not already one
        assert "if not isinstance(_m, MArray):" in code
        # Always sets value regardless of whether MArray existed
        assert "_m.value = state.U" in code

    def test_simple_var_default_scope_key(self):
        """Default scope_key is py_name."""
        ctx = _MockCtx(array_vars=set())
        emit_state_var_to_scope(ctx, "DT", "DT")
        code = ctx.emitter.get_code()
        assert "_scope.get('DT')" in code
        assert "_scope['DT'] = _m" in code


@pytest.mark.codegen
class TestEmitStateVarToScopeArray:
    """Verify generated code for array (subscripted) variables."""

    def test_array_var_assigns_directly(self):
        """Array var is assigned directly from state (no wrapping)."""
        ctx = _MockCtx(array_vars={"IO"})
        emit_state_var_to_scope(ctx, "IO", "IO")
        code = ctx.emitter.get_code()

        assert "_scope['IO'] = state.IO" in code
        # Should NOT have MArray wrapping logic
        assert "isinstance" not in code
        assert "_m = MArray()" not in code

    def test_array_var_preserves_subscripts(self):
        """Array var assignment doesn't extract .value (preserves children)."""
        ctx = _MockCtx(array_vars={"IO"})
        emit_state_var_to_scope(ctx, "IO", "IO")
        code = ctx.emitter.get_code()

        # Direct MArray assignment
        assert "_scope['IO'] = state.IO" in code
        # Should NOT extract .value
        assert ".value" not in code


@pytest.mark.codegen
class TestEmitStateVarToScopeScopeKey:
    """Verify scope_key override for state→scope sync."""

    def test_scope_key_differs_from_py_name(self):
        """scope_key parameter overrides the dictionary key used in _scope."""
        ctx = _MockCtx(array_vars=set())
        emit_state_var_to_scope(ctx, "X", "X", scope_key="X")
        code = ctx.emitter.get_code()
        assert "_scope.get('X')" in code
        assert "_m.value = state.X" in code

    def test_scope_key_with_original_mumps_name(self):
        """scope_key can use the original MUMPS name while py_name is translated."""
        ctx = _MockCtx(array_vars=set())
        emit_state_var_to_scope(ctx, "DT", "DT", scope_key="DT")
        code = ctx.emitter.get_code()
        # Scope key used for dict access
        assert "_scope.get('DT')" in code
        # py_name used for state attribute
        assert "_m.value = state.DT" in code

    def test_scope_key_for_array_var(self):
        """scope_key works with array vars too."""
        ctx = _MockCtx(array_vars={"IO"})
        emit_state_var_to_scope(ctx, "IO", "IO", scope_key="IO")
        code = ctx.emitter.get_code()
        assert "_scope['IO'] = state.IO" in code


# =============================================================================
# emit_scope_var_to_state  (scope→state direction)
# =============================================================================


@pytest.mark.codegen
class TestEmitScopeVarToStateSimple:
    """Verify generated code for simple (non-array) scope→state sync."""

    def test_simple_var_extracts_value(self):
        """Simple var extracts .value from MArray in _scope."""
        ctx = _MockCtx(array_vars=set())
        emit_scope_var_to_state(ctx, "X", "X")
        code = ctx.emitter.get_code()

        # Should check if key exists in _scope
        assert "if 'X' in _scope:" in code
        # Should extract .value for MArray, use plain value otherwise
        assert ".value" in code
        assert "isinstance" in code

    def test_simple_var_handles_non_marray(self):
        """Simple var falls back to plain value if _scope entry is not MArray."""
        ctx = _MockCtx(array_vars=set())
        emit_scope_var_to_state(ctx, "Y", "Y")
        code = ctx.emitter.get_code()
        # The isinstance check ensures non-MArray values pass through
        assert "isinstance" in code
        assert "else" in code


@pytest.mark.codegen
class TestEmitScopeVarToStateArray:
    """Verify generated code for array (subscripted) scope→state sync."""

    def test_array_var_preserves_marray(self):
        """Array var is assigned directly from _scope (preserves subscripts)."""
        ctx = _MockCtx(array_vars={"IO"})
        emit_scope_var_to_state(ctx, "IO", "IO")
        code = ctx.emitter.get_code()

        assert "state.IO = _scope['IO']" in code
        # Should NOT extract .value
        assert ".value" not in code

    def test_array_var_no_isinstance_check(self):
        """Array var path doesn't need isinstance check."""
        ctx = _MockCtx(array_vars={"IO"})
        emit_scope_var_to_state(ctx, "IO", "IO")
        code = ctx.emitter.get_code()
        assert "isinstance" not in code


@pytest.mark.codegen
class TestEmitScopeVarToStateScopeKey:
    """Verify scope_key override for scope→state sync."""

    def test_scope_key_overrides_dict_key(self):
        """scope_key parameter sets the dictionary key used for _scope lookup."""
        ctx = _MockCtx(array_vars=set())
        emit_scope_var_to_state(ctx, "X", "X", scope_key="X")
        code = ctx.emitter.get_code()
        assert "if 'X' in _scope:" in code

    def test_scope_key_with_array_var(self):
        """scope_key works with array vars."""
        ctx = _MockCtx(array_vars={"IO"})
        emit_scope_var_to_state(ctx, "IO", "IO", scope_key="IO")
        code = ctx.emitter.get_code()
        assert "state.IO = _scope['IO']" in code


# =============================================================================
# Symmetry: state_var_to_scope is inverse of scope_var_to_state
# =============================================================================


@pytest.mark.codegen
class TestSyncSymmetry:
    """Verify that state→scope and scope→state are conceptual inverses."""

    def test_simple_var_roundtrip_directions(self):
        """Both sync directions handle simple vars consistently.

        state→scope: wraps scalar in MArray
        scope→state: extracts .value from MArray
        Together they form a round-trip.
        """
        ctx1 = _MockCtx(array_vars=set())
        emit_state_var_to_scope(ctx1, "X", "X")
        to_scope = ctx1.emitter.get_code()

        ctx2 = _MockCtx(array_vars=set())
        emit_scope_var_to_state(ctx2, "X", "X")
        to_state = ctx2.emitter.get_code()

        # State→scope wraps in MArray
        assert "MArray()" in to_scope
        assert "_m.value" in to_scope
        # Scope→state extracts .value
        assert ".value" in to_state
        assert "isinstance" in to_state

    def test_array_var_roundtrip_directions(self):
        """Both sync directions handle array vars consistently.

        state→scope: assigns MArray directly
        scope→state: assigns MArray directly
        No wrapping/unwrapping needed.
        """
        ctx1 = _MockCtx(array_vars={"IO"})
        emit_state_var_to_scope(ctx1, "IO", "IO")
        to_scope = ctx1.emitter.get_code()

        ctx2 = _MockCtx(array_vars={"IO"})
        emit_scope_var_to_state(ctx2, "IO", "IO")
        to_state = ctx2.emitter.get_code()

        # Both directions: direct assignment, no wrapping
        assert "_scope['IO'] = state.IO" in to_scope
        assert "state.IO = _scope['IO']" in to_state
        assert "MArray()" not in to_scope
        assert "MArray()" not in to_state

    def test_var_not_in_array_vars_treated_as_simple(self):
        """A variable NOT in ctx.array_vars is treated as simple in both directions."""
        for fn in (emit_state_var_to_scope, emit_scope_var_to_state):
            ctx = _MockCtx(array_vars={"OTHER"})  # "Z" is NOT in array_vars
            fn(ctx, "Z", "Z")
            code = ctx.emitter.get_code()
            # Should have the simple path (with isinstance check)
            assert "isinstance" in code
