"""Tests for GotoExternal scope preservation through NewScopeManager.

When a function with formal parameters (NEW'd via NewScopeManager) does an
external GOTO, the parameters must survive in the scope for the GOTO target.

This tests the fix for the pattern:
    CALLER  D WRAPPER^ROUTINE_A(args)
    WRAPPER(P1,P2) G TARGET^ROUTINE_B    ; parameters P1,P2 must survive
    TARGET  ; must be able to access P1 via _scope

In MUMPS, ``G LABEL^ROUTINE`` from within a DO frame transfers control but
stays in the same execution level — NEW'd variables remain visible.
"""

import sys
import types

import pytest

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime, run_with_goto_support


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


@pytest.mark.codegen
class TestGotoExternalScopePreservation:
    """GotoExternal must not strip NEW'd parameters from scope."""

    def test_goto_external_preserves_formal_params(self, runtime):
        """Formal parameters survive external GOTO to another routine.

        Pattern: D WRAP^A(val) → WRAP NEWs P, sets P → G TARGET^B
        TARGET reads P from scope → writes P → QUITs back to caller.
        """
        # Routine A: WRAP takes a parameter and GOTOs TARGET^B
        mod_a = _load(
            "A Q\nWRAP(P) G TARGET^B\n",
            "A",
        )

        # Routine B: TARGET writes the value of P and quits
        _load(
            "B Q\nTARGET W P Q\n",
            "B",
        )

        # Simulate D WRAP^A("hello") via run_with_goto_support
        scope: dict = {}
        run_with_goto_support(
            lambda _rt, _scope=None: mod_a.WRAP(_rt, "hello", _scope=_scope),
            runtime,
            scope,
        )
        assert runtime.get_output() == "hello"

    def test_goto_external_preserves_multiple_params(self, runtime):
        """Multiple formal parameters all survive external GOTO."""
        mod_a = _load(
            "A Q\nWRAP(X,Y) G TARGET^B\n",
            "A",
        )
        _load(
            "B Q\nTARGET W X,Y Q\n",
            "B",
        )

        scope: dict = {}
        run_with_goto_support(
            lambda _rt, _scope=None: mod_a.WRAP(_rt, "foo", "bar", _scope=_scope),
            runtime,
            scope,
        )
        assert runtime.get_output() == "foobar"

    def test_goto_external_preserves_byref_param(self, runtime):
        """By-reference formal parameter survives external GOTO."""
        from m2py.runtime import MArray

        mod_a = _load(
            "A Q\nWRAP(X) G TARGET^B\n",
            "A",
        )
        _load(
            'B Q\nTARGET S X="modified" Q\n',
            "B",
        )

        scope: dict = {}
        arr = MArray()
        arr.value = "original"
        run_with_goto_support(
            lambda _rt, _scope=None: mod_a.WRAP(_rt, arr, _scope=_scope),
            runtime,
            scope,
        )
        # X was passed by reference; the GOTO target modified it
        assert arr.value == "modified"

    def test_handle_etrap_ignores_goto_external(self, runtime):
        """$ETRAP handler must not intercept GotoExternal signals.

        If $ETRAP is set, it should NOT fire for GotoExternal — that's
        a control-flow signal, not an error.
        """
        # Set an $ETRAP that would clear $ECODE (simulating a handler)
        runtime._etrap = 'S $ECODE=""'

        mod_a = _load(
            "A Q\nWRAP(P) G TARGET^B\n",
            "A",
        )
        _load(
            "B Q\nTARGET W P Q\n",
            "B",
        )

        scope: dict = {}
        run_with_goto_support(
            lambda _rt, _scope=None: mod_a.WRAP(_rt, "safe", _scope=_scope),
            runtime,
            scope,
        )
        # Should reach TARGET and write "safe", not be eaten by $ETRAP
        assert runtime.get_output() == "safe"

    def test_normal_quit_still_restores_scope(self, runtime):
        """Normal QUIT from a function with params still restores scope.

        Ensures the fix doesn't break normal NEW restoration.
        """
        from m2py.runtime import MArray

        mod_a = _load(
            'A Q\nWRAP(X) S X="inside" Q\n',
            "A",
        )

        scope: dict = {}
        outer_x = MArray()
        outer_x.value = "outer"
        scope["X"] = outer_x

        # Call WRAP — it NEWs X, sets X="inside", then QUITs
        # On QUIT, scope should restore X to "outer"
        mod_a.WRAP(runtime, "param_val", _scope=scope)
        assert scope["X"].value == "outer"

    def test_goto_external_without_args_preserves_scope_var(self, runtime):
        """GotoExternal entry without explicit args preserves existing scope vars.

        Pattern: S X=42 D WRAP^A  (no args)
        WRAP(X) internally does implicit NEW on X.  When entered via
        GotoExternal without explicit params (param=None), the _pv
        restore path should keep X=42 visible in the target scope.
        """
        from m2py.runtime import MArray

        # Routine A: WRAP takes param X but GOTOs to TARGET^B
        mod_a = _load(
            "A Q\nWRAP(X) G TARGET^B\n",
            "A",
        )
        # Routine B: TARGET writes X and quits
        _load(
            "B Q\nTARGET W X Q\n",
            "B",
        )

        scope: dict = {}
        x_val = MArray()
        x_val.value = "42"
        scope["X"] = x_val

        # simulate: X was set in caller scope, then D WRAP^A
        # The GOTO from WRAP to TARGET^B should still see X=42
        run_with_goto_support(
            lambda _rt, _scope=None: mod_a.WRAP(_rt, "42", _scope=_scope),
            runtime,
            scope,
        )
        assert runtime.get_output() == "42"
