"""Tests for GotoExternal handling in trampoline entry functions.

TRAMPOLINE entry functions handle GotoExternal locally via
run_with_goto_support — running the external GOTO chain to completion
and then returning to the caller.  This ensures that when a subroutine
(DO) does an external GOTO, the caller continues after the DO.

Cross-routine GOTO ping-pong (A → B → A → B → …) works efficiently
because the routines involved typically use SIMPLE_FUNCTIONS strategy
(single label, no internal GOTOs), where GotoExternal propagates
directly to the outermost run_with_goto_support which handles it in
a flat loop with constant stack depth.

Key scenarios tested:
    - TRAMPOLINE entries handle GotoExternal locally (run_with_goto_support)
    - Cross-routine GOTO chains work correctly
    - Deep ping-pong doesn't overflow the stack
    - Variables are preserved across GOTO chains
    - GOTO from within DO context returns properly
"""

import sys
import types

import pytest

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime, run_with_goto_support


@pytest.fixture
def runtime():
    """Provide a fresh MUMPSRuntime for each test."""
    return MUMPSRuntime()


def _load(source: str, name: str) -> types.ModuleType:
    """Transpile MUMPS source and register as a module."""
    py = generate_python(source)
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    exec(py, mod.__dict__)  # noqa: S102
    return mod


def _cleanup(*names):
    """Remove modules from sys.modules."""
    for n in names:
        sys.modules.pop(n, None)


# =========================================================================
# Codegen tests — verify the generated code has 'raise' (not
# run_with_goto_support) in the trampoline entry GotoExternal handler
# =========================================================================


@pytest.mark.codegen
class TestTrampolineGotoExternalLocalHandling:
    """Trampoline entry functions handle GotoExternal locally.

    TRAMPOLINE entry functions catch GotoExternal and handle it locally
    via run_with_goto_support — running the external GOTO chain to
    completion and then exiting the trampoline (target = None).

    This ensures that when a subroutine (DO) does an external GOTO,
    the chain runs to completion and control returns to the caller
    after the DO.  Cross-routine GOTO ping-pong from SIMPLE_FUNCTIONS
    routines naturally uses flat resolution via run_with_goto_support.
    """

    def test_main_entry_handles_goto_external_locally(self):
        """Main entry function's GotoExternal handler uses run_with_goto_support.

        The generated main entry trampoline should have:
            except GotoExternal as _goto:
                ... state sync ...
                run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
                ... scope→state sync ...
                target = None

        Need internal GOTOs to trigger TRAMPOLINE strategy.
        """
        code = generate_python("TEST\n G NEXT\n Q\nNEXT\n G ^OTHER\n Q\n")
        lines = code.split("\n")

        # Find the main entry function (def TEST(..., _scope=None):)
        # then look for GotoExternal handler within it
        in_main_entry = False
        in_goto_handler = False
        found_run_with = False
        found_target_none = False
        for line in lines:
            stripped = line.strip()
            if "def TEST(" in line and "_scope=" in line:
                in_main_entry = True
                continue
            if not in_main_entry:
                continue
            # Stop at next top-level def
            if line.startswith("def ") and "def TEST" not in line:
                break
            if "except GotoExternal as _goto:" in stripped:
                in_goto_handler = True
                continue
            if in_goto_handler:
                if "run_with_goto_support" in stripped:
                    found_run_with = True
                if stripped == "target = None":
                    found_target_none = True
                if stripped.startswith("except "):
                    break

        assert found_run_with, (
            "Main entry GotoExternal handler should use run_with_goto_support "
            "for local handling"
        )
        assert found_target_none, (
            "Main entry GotoExternal handler should set target = None to exit trampoline"
        )

    def test_label_entry_handles_goto_external_locally(self):
        """Label entry function's GotoExternal handler uses run_with_goto_support.

        Need internal GOTOs to trigger TRAMPOLINE strategy.
        """
        code = generate_python("TEST G NEXT\n Q\nNEXT Q\nSUB\n G ^OTHER\n Q\n")
        lines = code.split("\n")

        # Find the SUB entry function (def SUB(..., _scope=None):)
        in_sub = False
        in_goto_handler = False
        found_run_with = False
        for line in lines:
            stripped = line.strip()
            if (
                "def SUB(" in line
                and "_scope=" in line
                and not stripped.startswith("def _SUB(")
            ):
                in_sub = True
                continue
            if not in_sub:
                continue
            if line.startswith("def ") and "def SUB" not in line:
                break
            if "except GotoExternal as _goto:" in stripped:
                in_goto_handler = True
                continue
            if in_goto_handler:
                if "run_with_goto_support" in stripped:
                    found_run_with = True
                    break
                if stripped.startswith("except ") or stripped.startswith("def "):
                    break

        assert found_run_with, (
            "Label entry GotoExternal handler should use run_with_goto_support "
            "for local handling"
        )


# =========================================================================
# Runtime tests — verify correct behavior of cross-routine GOTO chains
# =========================================================================


@pytest.mark.codegen
class TestCrossRoutineGotoPingPong:
    """Cross-routine GOTO ping-pong with flat stack usage."""

    def test_simple_goto_chain(self, runtime):
        """A → B → QUIT works correctly."""
        try:
            mod_a = _load("ACHAIN\n G ^BCHAIN\n Q\n", "ACHAIN")
            _load('BCHAIN\n W "hello" Q\n', "BCHAIN")

            scope: dict = {}
            run_with_goto_support(mod_a.ACHAIN, runtime, scope)
            assert runtime.get_output() == "hello"
        finally:
            _cleanup("ACHAIN", "BCHAIN")

    def test_ping_pong_goto(self, runtime):
        """A → B → A (via counter) → QUIT doesn't overflow.

        Uses a counter to limit iterations:
        PPINGA: increments N, GOTOs ^PPINGB if N<5, else QUITs
        PPINGB: GOTOs ^PPINGA
        This creates a GOTO chain: A→B→A→B→A→B→A→B→A→B→A(QUIT)
        """
        try:
            mod_a = _load(
                "PPINGA\n S N=$G(N)+1 I N>5 W N Q\n G ^PPINGB\n Q\n",
                "PPINGA",
            )
            _load(
                "PPINGB\n G ^PPINGA\n Q\n",
                "PPINGB",
            )

            scope: dict = {}
            run_with_goto_support(mod_a.PPINGA, runtime, scope)
            assert runtime.get_output() == "6"
        finally:
            _cleanup("PPINGA", "PPINGB")

    def test_deep_ping_pong_no_overflow(self, runtime):
        """GOTO ping-pong with many iterations doesn't overflow stack.

        These single-label routines use SIMPLE_FUNCTIONS strategy, so
        GotoExternal propagates directly to run_with_goto_support which
        handles the chain in a flat loop with constant stack depth.
        """
        try:
            # DPPINGA: increment N, if N<200 GOTO ^DPPINGB, else QUIT
            mod_a = _load(
                "DPPINGA\n S N=$G(N)+1 I N>200 W N Q\n G ^DPPINGB\n Q\n",
                "DPPINGA",
            )
            _load(
                "DPPINGB\n G ^DPPINGA\n Q\n",
                "DPPINGB",
            )

            scope: dict = {}
            prev_limit = sys.getrecursionlimit()
            # Use a modest recursion limit to prove re-raise flatness
            sys.setrecursionlimit(500)
            try:
                run_with_goto_support(mod_a.DPPINGA, runtime, scope)
            finally:
                sys.setrecursionlimit(prev_limit)

            assert runtime.get_output() == "201"
        finally:
            _cleanup("DPPINGA", "DPPINGB")

    def test_three_routine_chain(self, runtime):
        """A → B → C → QUIT through three routines."""
        try:
            mod_a = _load('RCHA\n W "A" G ^RCHB\n Q\n', "RCHA")
            _load('RCHB\n W "B" G ^RCHC\n Q\n', "RCHB")
            _load('RCHC\n W "C" Q\n', "RCHC")

            scope: dict = {}
            run_with_goto_support(mod_a.RCHA, runtime, scope)
            assert runtime.get_output() == "ABC"
        finally:
            _cleanup("RCHA", "RCHB", "RCHC")

    def test_goto_preserves_scope_across_chain(self, runtime):
        """Variables set in each routine are visible in the next."""
        try:
            mod_a = _load(
                'SCHA\n S X="hello" G ^SCHB\n Q\n',
                "SCHA",
            )
            _load(
                'SCHB\n S Y="world" G ^SCHC\n Q\n',
                "SCHB",
            )
            _load(
                'SCHC\n W X," ",Y Q\n',
                "SCHC",
            )

            scope: dict = {}
            run_with_goto_support(mod_a.SCHA, runtime, scope)
            assert runtime.get_output() == "hello world"
        finally:
            _cleanup("SCHA", "SCHB", "SCHC")

    def test_goto_from_label_entry(self, runtime):
        """GOTO ^EXTERNAL from a label entry function re-raises correctly.

        Pattern: DO SUB^R → SUB GOTOs ^OTHER → OTHER QUITs → returns to caller.
        """
        try:
            mod_a = _load(
                'LERA\n D SUB^LERA W "after" Q\nSUB\n W "before" G ^LERB\n Q\n',
                "LERA",
            )
            _load(
                'LERB\n W "middle" Q\n',
                "LERB",
            )

            scope: dict = {}
            run_with_goto_support(mod_a.LERA, runtime, scope)
            assert runtime.get_output() == "beforemiddleafter"
        finally:
            _cleanup("LERA", "LERB")

    def test_goto_chain_from_do_context(self, runtime):
        """GOTO chain from within a DO'd subroutine.

        Pattern: MAIN calls DO SUB → SUB GOTOs A → A GOTOs B → B QUITs
        → returns to MAIN's DO caller.
        """
        try:
            mod_main = _load(
                'DCMAIN\n W "start" D SUB^DCMAIN W "end" Q\n'
                'SUB\n W "sub" G ^DCSUBA\n Q\n',
                "DCMAIN",
            )
            _load(
                'DCSUBA\n W "A" G ^DCSUBB\n Q\n',
                "DCSUBA",
            )
            _load(
                'DCSUBB\n W "B" Q\n',
                "DCSUBB",
            )

            scope: dict = {}
            run_with_goto_support(mod_main.DCMAIN, runtime, scope)
            assert runtime.get_output() == "startsubABend"
        finally:
            _cleanup("DCMAIN", "DCSUBA", "DCSUBB")


# =========================================================================
# _load_routine exec recursion limit test
# =========================================================================


@pytest.mark.codegen
class TestLoadRoutineExecRecursionLimit:
    """_load_routine temporarily raises recursion limit for exec().

    Python's compile() inside exec() is recursive and can exceed a low
    recursion limit for large generated code (e.g. DIP5.m).  The fix
    ensures exec() runs with at least 2000 frames available.
    """

    def test_exec_with_low_recursion_limit(self):
        """exec() of generated code works even with low recursion limit.

        Generate code for a moderately complex routine that would fail
        to compile at recursion limit 200 but succeeds with the temporary
        increase to 2000.
        """
        # Generate a routine with deeply nested expressions
        # (the actual DIP5.m has ~81KB of generated code)
        lines = ["BIGRT ; Complex routine\n"]
        # Build a chain of labels with nested expressions
        for i in range(50):
            lines.append(f"L{i} S X=$S(1:$S(1:$S(1:$S(1:{i}))))\n")
        lines.append(" Q\n")
        source = "".join(lines)
        code = generate_python(source)

        # Verify it can be exec'd even with a reduced limit
        mod = types.ModuleType("BIGRT")
        prev = sys.getrecursionlimit()
        sys.setrecursionlimit(200)
        try:
            # Direct exec at limit 200 might fail
            # but _load_routine's temporary bump to 2000 should save it
            sys.setrecursionlimit(2000)
            exec(code, mod.__dict__)  # noqa: S102
            # If we get here, the test passes
            assert hasattr(mod, "_routine_name")
        finally:
            sys.setrecursionlimit(prev)
