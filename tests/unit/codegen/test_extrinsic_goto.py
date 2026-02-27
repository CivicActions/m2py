"""Tests for GotoExternal handling inside extrinsic function calls.

When an extrinsic function ($$FUNC^ROUTINE) uses GOTO to redirect to another
routine's label, the GotoExternal exception must be caught by _call_extrinsic
and the target label executed in the same extrinsic context.  The target's
QUIT value becomes the extrinsic's return value.

Pattern:
    S X=$$CREF^DILF(Y)
    ; DILF's CREF does: G ENCREF^DIQGU
    ; DIQGU's ENCREF computes result and QUITs with value
    ; X receives that value

Previously, GotoExternal propagated uncaught through _call_extrinsic,
aborting the caller and losing variables set after the extrinsic call.
"""

import sys
import types

import pytest

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


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
# Core: extrinsic function with GOTO to another routine
# =============================================================================


@pytest.mark.codegen
class TestExtrinsicGotoRedirect:
    """_call_extrinsic must handle GOTO from within an extrinsic function."""

    def test_extrinsic_goto_returns_target_value(self, runtime):
        """$$FUNC^A does G TARGET^B; TARGET returns value → caller gets it.

        Pattern: CREF^DILF does G ENCREF^DIQGU, ENCREF returns result.
        """
        # Routine ROUTA: extrinsic FUNC does GOTO to TARGET^ROUTB
        _load(
            "ROUTA Q\nFUNC(X) G TARGET^ROUTB\n",
            "ROUTA",
        )
        # Routine ROUTB: TARGET reads X from _scope and returns
        _load(
            'ROUTB Q\nTARGET Q "got:"_X\n',
            "ROUTB",
        )
        # Routine CALLER: calls $$FUNC^ROUTA and writes the result
        mod_c = _load(
            'CALLER S V=$$FUNC^ROUTA("hello") W V Q\n',
            "CALLER",
        )

        scope: dict = {}
        mod_c.CALLER(runtime, _scope=scope)
        assert runtime.get_output() == "got:hello"

    def test_extrinsic_goto_no_args_target(self, runtime):
        """$$FUNC^A does G TARGET^B (no params on target); TARGET returns."""
        _load(
            'ROUTA Q\nFUNC(X) S Y=X_"!" G TARGET^ROUTB\n',
            "ROUTA",
        )
        _load(
            'ROUTB Q\nTARGET Q "done"\n',
            "ROUTB",
        )
        mod_c = _load(
            'CALLER S V=$$FUNC^ROUTA("test") W V Q\n',
            "CALLER",
        )

        scope: dict = {}
        mod_c.CALLER(runtime, _scope=scope)
        assert runtime.get_output() == "done"

    def test_extrinsic_goto_scope_visible_to_target(self, runtime):
        """Variables set before GOTO are visible to the target via _scope.

        The target should see variables set by the extrinsic before the GOTO.
        """
        _load(
            'ROUTA Q\nFUNC(X) S RESULT=X_"!" G TARGET^ROUTB\n',
            "ROUTA",
        )
        _load(
            "ROUTB Q\nTARGET Q RESULT\n",
            "ROUTB",
        )
        mod_c = _load(
            'CALLER S V=$$FUNC^ROUTA("hi") W V Q\n',
            "CALLER",
        )

        scope: dict = {}
        mod_c.CALLER(runtime, _scope=scope)
        assert runtime.get_output() == "hi!"

    def test_extrinsic_goto_chain(self, runtime):
        """Extrinsic GOTO chains: A → B → C, C returns the value.

        Tests multiple GotoExternal exceptions in sequence.
        """
        _load(
            "ROUTA Q\nFUNC(X) G MID^ROUTB\n",
            "ROUTA",
        )
        _load(
            "ROUTB Q\nMID G FINAL^ROUTC\n",
            "ROUTB",
        )
        _load(
            'ROUTC Q\nFINAL Q "chain_ok"\n',
            "ROUTC",
        )
        mod_d = _load(
            "CALLER S V=$$FUNC^ROUTA(1) W V Q\n",
            "CALLER",
        )

        scope: dict = {}
        mod_d.CALLER(runtime, _scope=scope)
        assert runtime.get_output() == "chain_ok"

    def test_extrinsic_goto_preserves_test(self, runtime):
        """$TEST is preserved across extrinsic calls with GOTO.

        Extrinsic functions must not alter the caller's $TEST.
        """
        _load(
            "ROUTA Q\nFUNC() G TARGET^ROUTB\n",
            "ROUTA",
        )
        # TARGET sets $TEST via IF, then returns
        _load(
            'ROUTB Q\nTARGET I 0 Q "no"\n Q "yes"\n',
            "ROUTB",
        )
        # Caller sets $TEST=1 via I 1, then calls extrinsic, then checks $TEST
        mod_c = _load(
            "CALLER I 1 S V=$$FUNC^ROUTA() W $T Q\n",
            "CALLER",
        )

        scope: dict = {}
        mod_c.CALLER(runtime, _scope=scope)
        # $TEST should still be 1 (caller's value), not 0 (callee's value)
        assert runtime.get_output() == "1"


# =============================================================================
# Edge cases
# =============================================================================


@pytest.mark.codegen
class TestExtrinsicGotoEdgeCases:
    """Edge cases for GotoExternal in extrinsic functions."""

    def test_extrinsic_without_goto_still_works(self, runtime):
        """Normal extrinsic (no GOTO) continues to work correctly."""
        _load(
            'ROUTA Q\nFUNC(X) Q X_"!"\n',
            "ROUTA",
        )
        mod_c = _load(
            'CALLER S V=$$FUNC^ROUTA("ok") W V Q\n',
            "CALLER",
        )

        scope: dict = {}
        mod_c.CALLER(runtime, _scope=scope)
        assert runtime.get_output() == "ok!"

    def test_extrinsic_goto_with_scope_vars(self, runtime):
        """Extrinsic GOTO preserves scope variables set by caller.

        Caller sets ARR, extrinsic does GOTO, target reads ARR.
        """
        _load(
            "ROUTA Q\nFUNC() G TARGET^ROUTB\n",
            "ROUTA",
        )
        _load(
            "ROUTB Q\nTARGET Q ARR\n",
            "ROUTB",
        )
        mod_c = _load(
            'CALLER S ARR="orig" S V=$$FUNC^ROUTA() W V Q\n',
            "CALLER",
        )

        scope: dict = {}
        mod_c.CALLER(runtime, _scope=scope)
        output = runtime.get_output()
        assert output == "orig"

    def test_extrinsic_goto_callee_sets_vars_after(self, runtime):
        """Variables set AFTER the extrinsic call are not lost.

        This is the DIKVAL pattern: caller calls $$CREF via _call_extrinsic,
        then sets variables afterward. If GotoExternal propagated uncaught,
        those subsequent SETs would never execute.
        """
        _load(
            "ROUTA Q\nCREF(X) G ENCREF^ROUTB\n",
            "ROUTA",
        )
        _load(
            'ROUTB Q\nENCREF Q "result"\n',
            "ROUTB",
        )
        # MAIN: calls $$CREF, then sets AFTER="yes", writes both
        mod_c = _load(
            'MAIN S V=$$CREF^ROUTA("x") S AFTER="yes" W V,AFTER Q\n',
            "MAIN",
        )

        scope: dict = {}
        mod_c.MAIN(runtime, _scope=scope)
        output = runtime.get_output()
        assert output == "resultyes"

    def test_extrinsic_goto_inside_new_scope(self, runtime):
        """Extrinsic GOTO from within a NewScopeManager (DICTRL pattern).

        When DICTRL has `with NewScopeManager` and calls $$CREF^DILF
        which does GOTO, the GOTO must be handled without disrupting
        the NewScopeManager context.
        """
        _load(
            "ROUTA Q\nCREF(X) G ENCREF^ROUTB\n",
            "ROUTA",
        )
        _load(
            'ROUTB Q\nENCREF Q "closed_ref"\n',
            "ROUTB",
        )
        # Routine with NEW that calls the extrinsic
        mod_c = _load(
            'MAIN\n N RESULT\n S RESULT=$$CREF^ROUTA("x")\n W RESULT\n Q\n',
            "MAIN",
        )

        scope: dict = {}
        mod_c.MAIN(runtime, _scope=scope)
        assert runtime.get_output() == "closed_ref"

    def test_extrinsic_goto_void_quit(self, runtime):
        """Extrinsic GOTO target does Q (no value) in non-extrinsic context.

        When the target QUIT has no value and $QUIT=1 (extrinsic context),
        it should return empty string.
        """
        _load(
            "ROUTA Q\nFUNC() G TARGET^ROUTB\n",
            "ROUTA",
        )
        _load(
            'ROUTB Q\nTARGET Q ""\n',
            "ROUTB",
        )
        mod_c = _load(
            'CALLER S V=$$FUNC^ROUTA() W "["_V_"]" Q\n',
            "CALLER",
        )

        scope: dict = {}
        mod_c.CALLER(runtime, _scope=scope)
        assert runtime.get_output() == "[]"


# =============================================================================
# _call_extrinsic codegen: verify generated code structure
# =============================================================================


@pytest.mark.codegen
class TestCallExtrinsicCodegen:
    """Verify _call_extrinsic template includes GotoExternal handling."""

    def test_call_extrinsic_has_goto_handler(self):
        """Generated _call_extrinsic contains GotoExternal catch block."""
        code = generate_python("TEST Q\n")
        assert "except GotoExternal as _goto:" in code
        assert "resolve_goto_target(_goto)" in code

    def test_call_extrinsic_has_while_loop(self):
        """Generated _call_extrinsic uses while loop for GOTO chaining."""
        code = generate_python("TEST Q\n")
        # Find _call_extrinsic function
        lines = code.split("\n")
        in_func = False
        func_lines = []
        for line in lines:
            if "def _call_extrinsic" in line:
                in_func = True
            if in_func:
                func_lines.append(line)
                if line.strip() == "" and len(func_lines) > 5:
                    break

        func_text = "\n".join(func_lines)
        assert "while True:" in func_text
        assert "break" in func_text  # normal path breaks out of loop

    def test_call_extrinsic_preserves_byref_handling(self):
        """GotoExternal handling doesn't break by-ref unpacking."""
        code = generate_python("TEST Q\n")
        # By-ref handling should still exist after the while loop
        assert "_byref_idx" in code
        assert "_scope.setdefault(_name, MArray()).value" in code
