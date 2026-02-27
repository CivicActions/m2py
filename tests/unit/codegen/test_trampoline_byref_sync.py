"""Tests for TRAMPOLINE by-ref DO scope sync.

When a TRAMPOLINE-mode routine calls a local label with by-reference
arguments (e.g., ``D INIZE^DIEFU(.DIFILE)``), the codegen must:

1. Forward sync: ``state._locals → _scope`` before the call so the callee
   sees current variable values.
2. Back sync: ``_scope → state._locals`` after the call returns so the
   caller sees variables SET by the callee.

Without this sync, variables NEWed or SET only in ``state._locals`` are
invisible to the callee, and variables SET by the callee (propagated back
to ``_scope`` on return) are lost when the next call overwrites ``_scope``
from stale ``state._locals``.

The specific bug this fixes: DIKJ was set by DO DISKIPIN inside a
TRAMPOLINE routine (DIKC.m). DISKIPIN called DDGO which fell through
to DIKJ label, setting DIKJ in _scope. But the back sync was missing,
so DIKJ never made it back to state._locals, causing KeyError later.
"""

import sys
import types

import pytest

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime, run_with_goto_support


@pytest.fixture(autouse=True)
def _cleanup_modules():
    """Remove test modules from sys.modules after each test."""
    before = set(sys.modules)
    yield
    for name in set(sys.modules) - before:
        del sys.modules[name]


@pytest.fixture
def runtime():
    """Provide a fresh runtime for each test."""
    return MUMPSRuntime()


def _load(source: str, name: str) -> types.ModuleType:
    """Transpile MUMPS source and register as a module."""
    py = generate_python(source)
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    exec(py, mod.__dict__)  # noqa: S102
    return mod


# =============================================================================
# Runtime: by-ref DO calls propagate variables correctly
# =============================================================================


@pytest.mark.codegen
class TestByrefDoScopeSync:
    """Variables SET inside by-ref DO calls must be visible to the caller."""

    def test_byref_do_sets_variable_visible_to_caller(self, runtime):
        """Callee sets a variable; caller can read it after the DO.

        Pattern: D INIT(.X), where INIT sets Y="value" → caller reads Y.
        """
        mod = _load(
            'MAIN\n S X=""\n D SUB(.X)\n W Y\n Q\nSUB(P) S Y="hello" Q\n',
            "MAIN",
        )

        scope: dict = {}
        run_with_goto_support(
            lambda _rt, _scope=None: mod.MAIN(_rt, _scope=_scope),
            runtime,
            scope,
        )
        assert runtime.get_output() == "hello"

    def test_byref_do_modifies_ref_param(self, runtime):
        """By-ref parameter is modified by callee; caller sees the change."""
        mod = _load(
            'MAIN\n S X="original"\n D SUB(.X)\n W X\n Q\nSUB(P) S P="modified" Q\n',
            "MAIN",
        )

        scope: dict = {}
        run_with_goto_support(
            lambda _rt, _scope=None: mod.MAIN(_rt, _scope=_scope),
            runtime,
            scope,
        )
        assert runtime.get_output() == "modified"

    def test_byref_do_caller_new_visible_to_callee(self, runtime):
        """Variables NEWed by caller are visible to callee via forward sync.

        Pattern: N DIKVAL  D CHK(.X) — callee should see empty DIKVAL.
        """
        mod = _load(
            'MAIN\n N Z\n S Z="fresh"\n D SUB(.Z)\n W Y\n Q\nSUB(P) S Y=P Q\n',
            "MAIN",
        )

        scope: dict = {}
        run_with_goto_support(
            lambda _rt, _scope=None: mod.MAIN(_rt, _scope=_scope),
            runtime,
            scope,
        )
        assert runtime.get_output() == "fresh"

    def test_byref_do_multiple_vars_sync(self, runtime):
        """Multiple variables SET by callee all propagate back to caller."""
        mod = _load(
            'MAIN\n S X=""\n D INIT(.X)\n W A,B,C\n Q\nINIT(P) S A=1,B=2,C=3 Q\n',
            "MAIN",
        )

        scope: dict = {}
        run_with_goto_support(
            lambda _rt, _scope=None: mod.MAIN(_rt, _scope=_scope),
            runtime,
            scope,
        )
        assert runtime.get_output() == "123"

    def test_byref_do_stale_vars_cleaned(self, runtime):
        """Variables KILLed by caller before DO don't leak to callee.

        Forward sync should remove stale _scope entries for variables
        no longer in state._locals.
        """
        mod = _load(
            "MAIN\n S X=1,Y=2\n K Y\n D SUB(.X)\n Q\nSUB(P) W $D(Y) Q\n",
            "MAIN",
        )

        scope: dict = {}
        run_with_goto_support(
            lambda _rt, _scope=None: mod.MAIN(_rt, _scope=_scope),
            runtime,
            scope,
        )
        # $D(Y) should be 0 (undefined), not 1
        assert runtime.get_output() == "0"


# =============================================================================
# Codegen: verify generated code includes sync
# =============================================================================


@pytest.mark.codegen
class TestByrefDoCodegen:
    """Generated code for by-ref DO in TRAMPOLINE mode includes sync."""

    def test_trampoline_byref_has_forward_sync(self):
        """TRAMPOLINE by-ref DO generates forward sync (state→scope)."""
        # A large enough routine that uses TRAMPOLINE strategy with by-ref
        # We need multiple labels to trigger TRAMPOLINE
        source = (
            "MAIN\n S X=1\n D SUB(.X)\n W X\n Q\nSUB(P)\n S P=2\n Q\nOTHER\n G MAIN\n"
        )
        code = generate_python(source)
        # Should contain _scope.update for forward sync before the by-ref call
        assert "_scope.update" in code or "state._locals.items()" in code

    def test_trampoline_byref_has_back_sync(self):
        """TRAMPOLINE by-ref DO generates back sync (scope→state)."""
        source = (
            "MAIN\n S X=1\n D SUB(.X)\n W X\n Q\nSUB(P)\n S P=2\n Q\nOTHER\n G MAIN\n"
        )
        code = generate_python(source)
        # Should contain _scope.items() for back sync after by-ref call
        assert "_scope.items()" in code


# =============================================================================
# Cross-routine: by-ref DO to external routine
# =============================================================================


@pytest.mark.codegen
class TestByrefExternalDoSync:
    """By-ref DO to external routine propagates scope correctly."""

    def test_external_byref_do_propagates_back(self, runtime):
        """External DO with by-ref args: callee's vars visible to caller.

        Pattern: D INIT^EXT(.X) where EXT sets RESULT → caller reads RESULT.
        """
        _load(
            'EXT Q\nINIT(P) S P=P_"!" S RESULT="done" Q\n',
            "EXT",
        )
        mod_main = _load(
            'MAIN S X="test" D INIT^EXT(.X) W X,RESULT Q\n',
            "MAIN",
        )

        scope: dict = {}
        run_with_goto_support(
            lambda _rt, _scope=None: mod_main.MAIN(_rt, _scope=_scope),
            runtime,
            scope,
        )
        output = runtime.get_output()
        assert "test!" in output
        assert "done" in output

    def test_successive_byref_calls_dont_lose_vars(self, runtime):
        """Two successive by-ref DO calls — second sees vars from first.

        Pattern:
            D FIRST(.X)   ; sets A=1
            D SECOND(.X)  ; should see A=1, sets B=2
            W A,B          ; should be 12
        """
        mod = _load(
            "MAIN\n"
            " S X=0\n"
            " D FIRST(.X)\n"
            " D SECOND(.X)\n"
            " W A,B\n"
            " Q\n"
            "FIRST(P) S A=1 Q\n"
            "SECOND(P) S B=2 Q\n",
            "MAIN",
        )

        scope: dict = {}
        run_with_goto_support(
            lambda _rt, _scope=None: mod.MAIN(_rt, _scope=_scope),
            runtime,
            scope,
        )
        assert runtime.get_output() == "12"
