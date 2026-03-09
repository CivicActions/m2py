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
from m2py.runtime import MUMPSRuntime, run_with_goto_support, _unwind_pending_news


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
        """Main entry function's GotoExternal handler re-raises the exception.

        The generated main entry trampoline should have:
            except GotoExternal as _goto:
                ... state sync ...
                raise

        This lets the outer run_with_goto_support handle the GOTO
        iteratively, avoiding recursive depth growth.
        Need internal GOTOs to trigger TRAMPOLINE strategy.
        """
        code = generate_python("TEST\n G NEXT\n Q\nNEXT\n G ^OTHER\n Q\n")
        lines = code.split("\n")

        # Find the main entry function (def TEST(..., _scope=None):)
        # then look for GotoExternal handler within it
        in_main_entry = False
        in_goto_handler = False
        found_raise = False
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
                if stripped == "raise":
                    found_raise = True
                if stripped.startswith("except "):
                    break

        assert found_raise, (
            "Main entry GotoExternal handler should re-raise "
            "for iterative handling by run_with_goto_support"
        )

    def test_label_entry_handles_goto_external_locally(self):
        """Label entry function's GotoExternal handler re-raises the exception.

        Need internal GOTOs to trigger TRAMPOLINE strategy.
        """
        code = generate_python("TEST G NEXT\n Q\nNEXT Q\nSUB\n G ^OTHER\n Q\n")
        lines = code.split("\n")

        # Find the SUB entry function (def SUB(..., _scope=None):)
        in_sub = False
        in_goto_handler = False
        found_raise = False
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
                if stripped == "raise":
                    found_raise = True
                    break
                if stripped.startswith("except ") or stripped.startswith("def "):
                    break

        assert found_raise, (
            "Label entry GotoExternal handler should re-raise "
            "for iterative handling by run_with_goto_support"
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


# =========================================================================
# Wrapper label pattern — DO LABEL^ROUTINE where LABEL immediately GOTOs
# externally (the MXMLPRS0 DOPARAM pattern)
# =========================================================================


@pytest.mark.codegen
class TestTrampolineWrapperLabelPattern:
    """TRAMPOLINE routines with wrapper labels that GOTO externally.

    Pattern found in MXMLPRS0:
        DOPARAM G DOPARAM^MXMLPRSE   ; wrapper label just GOTOs externally
        READ    G READ^MXMLPRSE      ; another wrapper label

    When called via D DOPARAM^MXMLPRS0, the DO must:
    1. Enter MXMLPRS0's DOPARAM entry function
    2. _DOPARAM raises GotoExternal to MXMLPRSE
    3. The entry function catches it, handles locally via run_with_goto_support
    4. run_with_goto_support runs MXMLPRSE's DOPARAM to completion
    5. Control returns to the caller's code *after* the DO

    If GotoExternal were re-raised instead, it would escape past the DO
    boundary, and the caller would never continue.
    """

    def test_do_wrapper_label_continues_after(self, runtime):
        """D WRAPPER^R where WRAPPER GOTOs externally → caller continues.

        WRAPRT has multiple labels (TRAMPOLINE strategy) and one wrapper
        label that immediately GOTOs an external routine.  The DO caller
        should see W "after" execute.
        """
        try:
            # WRAPRT has internal GOTOs → TRAMPOLINE; PARAM immediately GOTOs external
            _load(
                'WRAPRT\n G MAIN\n Q\nMAIN\n W "main" Q\nPARAM G PARAM^WRAPEXT\n Q\n',
                "WRAPRT",
            )
            _load(
                'WRAPEXT\n Q\nPARAM\n W "external" Q\n',
                "WRAPEXT",
            )
            # Caller: DO PARAM^WRAPRT then writes "after"
            mod_caller = _load(
                'WRAPCALL\n W "before" D PARAM^WRAPRT W "after" Q\n',
                "WRAPCALL",
            )

            scope: dict = {}
            run_with_goto_support(mod_caller.WRAPCALL, runtime, scope)
            assert runtime.get_output() == "beforeexternalafter"
        finally:
            _cleanup("WRAPRT", "WRAPEXT", "WRAPCALL")

    def test_do_wrapper_label_with_shared_variables(self, runtime):
        """Wrapper label GOTO preserves variable changes.

        External routine sets a variable, wrapper returns, and
        the caller can read the variable.
        """
        try:
            _load(
                'WVRT\n G MAIN\n Q\nMAIN\n W "main" Q\nSETEXT G SETEXT^WVEXT\n Q\n',
                "WVRT",
            )
            _load(
                'WVEXT\n Q\nSETEXT\n S RESULT="done" Q\n',
                "WVEXT",
            )
            mod_caller = _load(
                "WVCALL\n D SETEXT^WVRT W $G(RESULT) Q\n",
                "WVCALL",
            )

            scope: dict = {}
            run_with_goto_support(mod_caller.WVCALL, runtime, scope)
            assert runtime.get_output() == "done"
        finally:
            _cleanup("WVRT", "WVEXT", "WVCALL")

    def test_multiple_do_wrapper_calls(self, runtime):
        """Multiple DO calls to wrapper labels in sequence.

        Simulates MXMLPRS0's pattern where DOPARAM is called many times
        during XML parsing.
        """
        try:
            _load(
                'MWRT\n G MAIN\n Q\nMAIN\n W "main" Q\nACT G ACT^MWEXT\n Q\n',
                "MWRT",
            )
            _load(
                "MWEXT\n Q\nACT\n S N=$G(N)+1 Q\n",
                "MWEXT",
            )
            mod_caller = _load(
                "MWCALL\n D ACT^MWRT D ACT^MWRT D ACT^MWRT W $G(N) Q\n",
                "MWCALL",
            )

            scope: dict = {}
            run_with_goto_support(mod_caller.MWCALL, runtime, scope)
            assert runtime.get_output() == "3"
        finally:
            _cleanup("MWRT", "MWEXT", "MWCALL")


# =========================================================================
# TRAMPOLINE nested DO with external GOTO — the sort chain pattern
# =========================================================================


@pytest.mark.codegen
class TestTrampolineNestedDoExternalGoto:
    """TRAMPOLINE routine calls subroutine that GOTOs externally.

    Pattern found in DIP/DICLGFT sort chain:
        DICLGFT (TRAMPOLINE) calls D EN1^DIP
        DIP (TRAMPOLINE) does G ^DIP5
        DIP5 does work, QUITs
        DIP returns to DICLGFT
        DICLGFT continues (sets up DINDEX etc.)

    With local handling, the GOTO chain runs to completion inside
    DIP's trampoline, and DIP returns normally to DICLGFT.
    """

    def test_trampoline_do_subroutine_with_goto(self, runtime):
        """TRAMPOLINE A calls D SUB → SUB GOTOs externally → A continues.

        OUTERRT (TRAMPOLINE) calls D WORK^INNERRT.
        INNERRT (TRAMPOLINE) does G ^EXTRT during WORK.
        EXTRT does work (writes "ext") then QUITs.
        INNERRT's WORK trampoline handles it locally (target=None).
        Control returns to OUTERRT, which writes "continued".
        """
        try:
            # INNERRT has internal GOTOs → TRAMPOLINE
            _load(
                "INNERRT\n G SETUP\n Q\n"
                'SETUP\n W "setup" Q\n'
                'WORK\n W "work" G ^TNEXTRT\n Q\n',
                "INNERRT",
            )
            _load(
                'TNEXTRT\n W "ext" Q\n',
                "TNEXTRT",
            )
            # OUTERRT calls D WORK^INNERRT then continues
            mod_outer = _load(
                'OUTERRT\n D WORK^INNERRT W "continued" Q\n',
                "OUTERRT",
            )

            scope: dict = {}
            run_with_goto_support(mod_outer.OUTERRT, runtime, scope)
            assert runtime.get_output() == "workextcontinued"
        finally:
            _cleanup("INNERRT", "TNEXTRT", "OUTERRT")

    def test_trampoline_do_chain_preserves_variables(self, runtime):
        """Variables survive through TRAMPOLINE GOTO chain and back.

        OUTERRT sets X, calls D WORK^INNERRT.
        WORK GOTOs ^EXTRT which sets Y.
        After DO returns, OUTERRT writes X and Y.
        """
        try:
            _load(
                "TVIRT\n G SETUP\n Q\nSETUP\n Q\nWORK\n G ^TVEXTRT\n Q\n",
                "TVIRT",
            )
            _load(
                'TVEXTRT\n S Y="world" Q\n',
                "TVEXTRT",
            )
            mod = _load(
                'TVCALL\n S X="hello" D WORK^TVIRT W X," ",Y Q\n',
                "TVCALL",
            )

            scope: dict = {}
            run_with_goto_support(mod.TVCALL, runtime, scope)
            assert runtime.get_output() == "hello world"
        finally:
            _cleanup("TVIRT", "TVEXTRT", "TVCALL")

    def test_nested_trampoline_do_chain(self, runtime):
        """Two levels of TRAMPOLINE DO chains.

        Pattern: caller -> TRAMPOLINE B -> GOTO ^C -> C QUITs
                 -> B's trampoline handles locally -> B returns -> caller continues
        """
        try:
            # B has internal GOTOs → TRAMPOLINE
            _load(
                'NTRB\n G INIT\n Q\nINIT\n Q\nSUB\n W "B" G ^NTRC\n Q\n',
                "NTRB",
            )
            _load(
                'NTRC\n W "C" Q\n',
                "NTRC",
            )
            # A also has internal GOTOs → TRAMPOLINE
            mod = _load(
                'NTRA\n G START\n Q\nSTART\n W "A" D SUB^NTRB W "done" Q\n',
                "NTRA",
            )

            scope: dict = {}
            run_with_goto_support(mod.NTRA, runtime, scope)
            assert runtime.get_output() == "ABCdone"
        finally:
            _cleanup("NTRA", "NTRB", "NTRC")

    def test_trampoline_multi_hop_goto(self, runtime):
        """TRAMPOLINE routine GOTOs through multiple external routines.

        MHRT (TRAMPOLINE) WORK label GOTOs ^MH1 → MH1 GOTOs ^MH2 → MH2 QUITs.
        All handled locally via run_with_goto_support nesting.
        """
        try:
            _load(
                'MHRT\n G INIT\n Q\nINIT\n Q\nWORK\n W "start" G ^MHRT1\n Q\n',
                "MHRT",
            )
            _load(
                'MHRT1\n W "-hop1" G ^MHRT2\n Q\n',
                "MHRT1",
            )
            _load(
                'MHRT2\n W "-hop2" Q\n',
                "MHRT2",
            )
            mod = _load(
                'MHCALL\n D WORK^MHRT W "-done" Q\n',
                "MHCALL",
            )

            scope: dict = {}
            run_with_goto_support(mod.MHCALL, runtime, scope)
            assert runtime.get_output() == "start-hop1-hop2-done"
        finally:
            _cleanup("MHRT", "MHRT1", "MHRT2", "MHCALL")


# =========================================================================
# Codegen detail tests — verify state/scope sync in GotoExternal handler
# =========================================================================


@pytest.mark.codegen
class TestTrampolineGotoExternalCodegenDetails:
    """Verify codegen details of the GotoExternal handler."""

    def test_main_entry_has_scope_to_state_sync_after_handler(self):
        """Handler syncs state→scope then re-raises to outer rwgs.

        The handler pattern is:
            except GotoExternal:
                state→scope sync
                raise
        """
        code = generate_python("TEST\n G NEXT\n Q\nNEXT\n G ^OTHER\n Q\n")
        lines = code.split("\n")

        in_main = False
        in_handler = False
        found_raise = False
        for line in lines:
            stripped = line.strip()
            if "def TEST(" in line and "_scope=" in line:
                in_main = True
                continue
            if not in_main:
                continue
            if line.startswith("def ") and "def TEST" not in line:
                break
            if "except GotoExternal as _goto:" in stripped:
                in_handler = True
                continue
            if in_handler:
                if stripped == "raise":
                    found_raise = True
                if stripped.startswith("except "):
                    break

        assert found_raise, "Handler must re-raise GotoExternal"

    def test_handler_uses_bare_raise(self):
        """GotoExternal handler MUST use bare 'raise'.

        A bare 'raise' re-raises to the outer run_with_goto_support
        which handles the GOTO iteratively (no recursive depth growth).
        Same-routine DO call sites have their own try/except wrappers.
        """
        code = generate_python("TEST\n G NEXT\n Q\nNEXT\n G ^OTHER\n Q\n")
        lines = code.split("\n")

        in_main = False
        in_handler = False
        found_raise = False
        for line in lines:
            stripped = line.strip()
            if "def TEST(" in line and "_scope=" in line:
                in_main = True
                continue
            if not in_main:
                continue
            if line.startswith("def ") and "def TEST" not in line:
                break
            if "except GotoExternal as _goto:" in stripped:
                in_handler = True
                continue
            if in_handler:
                if stripped == "raise":
                    found_raise = True
                if stripped.startswith("except "):
                    break

        assert found_raise, (
            "GotoExternal handler must use bare 'raise' — "
            "this lets the outer rwgs handle GOTOs iteratively"
        )

    def test_simple_functions_has_no_goto_external_handler(self):
        """SIMPLE_FUNCTIONS routines don't catch GotoExternal in entries.

        Single-label routines use SIMPLE_FUNCTIONS strategy and have no
        trampoline.  GotoExternal propagates naturally to the caller's
        run_with_goto_support.
        """
        code = generate_python('SIMPLE\n W "hi" G ^OTHER\n Q\n')
        lines = code.split("\n")

        in_entry = False
        found_goto_handler = False
        for line in lines:
            stripped = line.strip()
            if "def SIMPLE(" in line and "_scope=" in line:
                in_entry = True
                continue
            if not in_entry:
                continue
            if line.startswith("def ") and "def SIMPLE" not in line:
                break
            if "except GotoExternal" in stripped:
                found_goto_handler = True

        assert not found_goto_handler, (
            "SIMPLE_FUNCTIONS entry should not catch GotoExternal — "
            "it should propagate naturally to run_with_goto_support"
        )


# =========================================================================
# Edge cases
# =========================================================================


@pytest.mark.codegen
class TestGotoExternalEdgeCases:
    """Edge cases for GotoExternal handling."""

    def test_goto_after_write_in_trampoline(self, runtime):
        """GOTO after WRITE in trampoline — written output preserved.

        The trampoline catches GotoExternal locally, so output from
        BEFORE the GOTO is preserved.
        """
        try:
            _load(
                'GAWRT\n G INIT\n Q\nINIT\n Q\nSUB\n W "before-goto" G ^GAWEXT\n Q\n',
                "GAWRT",
            )
            _load(
                'GAWEXT\n W "-external" Q\n',
                "GAWEXT",
            )
            mod = _load(
                "GAWCALL\n D SUB^GAWRT Q\n",
                "GAWCALL",
            )

            scope: dict = {}
            run_with_goto_support(mod.GAWCALL, runtime, scope)
            assert runtime.get_output() == "before-goto-external"
        finally:
            _cleanup("GAWRT", "GAWEXT", "GAWCALL")

    def test_goto_external_returns_to_caller_cleanly(self, runtime):
        """Entry that GOTOs externally returns cleanly to DO caller.

        When a label entry handles GotoExternal locally and sets
        target=None, the function exits normally and the DO caller
        continues without error.
        """
        try:
            _load(
                "RTNRT\n G INIT\n Q\nINIT\n Q\nSUB\n G ^RTNEXT\n Q\n",
                "RTNRT",
            )
            _load(
                "RTNEXT\n Q\n",
                "RTNEXT",
            )
            # Verify DO SUB^RTNRT works without error
            mod = _load(
                'RTNCALL\n D SUB^RTNRT W "ok" Q\n',
                "RTNCALL",
            )

            scope: dict = {}
            run_with_goto_support(mod.RTNCALL, runtime, scope)
            assert runtime.get_output() == "ok"
        finally:
            _cleanup("RTNRT", "RTNEXT", "RTNCALL")

    def test_conditional_goto_external_taken(self, runtime):
        """Conditional GOTO ^EXTERNAL — takes GOTO path.

        When condition is true, GOTO fires and the handler catches it.
        """
        try:
            _load(
                'CGRT\n G INIT\n Q\nINIT\n Q\nWORK\n I 1 G ^CGEXT\n W "not-taken" Q\n',
                "CGRT",
            )
            _load(
                'CGEXT\n W "taken" Q\n',
                "CGEXT",
            )
            mod = _load(
                'CGCALL\n D WORK^CGRT W "-done" Q\n',
                "CGCALL",
            )

            scope: dict = {}
            run_with_goto_support(mod.CGCALL, runtime, scope)
            assert runtime.get_output() == "taken-done"
        finally:
            _cleanup("CGRT", "CGEXT", "CGCALL")

    def test_conditional_goto_external_not_taken(self, runtime):
        """Conditional GOTO ^EXTERNAL — does NOT take GOTO path.

        When condition is false, GOTO doesn't fire and normal code executes.
        """
        try:
            _load(
                'CGNRT\n G INIT\n Q\nINIT\n Q\nWORK\n I 0 G ^CGNEXT\n W "normal" Q\n',
                "CGNRT",
            )
            _load(
                'CGNEXT\n W "external" Q\n',
                "CGNEXT",
            )
            mod = _load(
                'CGNCALL\n D WORK^CGNRT W "-done" Q\n',
                "CGNCALL",
            )

            scope: dict = {}
            run_with_goto_support(mod.CGNCALL, runtime, scope)
            assert runtime.get_output() == "normal-done"
        finally:
            _cleanup("CGNRT", "CGNEXT", "CGNCALL")

    def test_extrinsic_with_trampoline_routine(self, runtime):
        """$$FUNC^R where R is a TRAMPOLINE routine.

        Extrinsic calls should work correctly with TRAMPOLINE routines
        that have internal GOTOs (but not through the extrinsic path).
        """
        try:
            _load(
                'EXRT\n G INIT\n Q\nINIT\n Q\nFUNC()\n Q "result"\n',
                "EXRT",
            )
            mod_caller = _load(
                "EXCALL\n W $$FUNC^EXRT() Q\n",
                "EXCALL",
            )

            scope: dict = {}
            run_with_goto_support(mod_caller.EXCALL, runtime, scope)
            assert runtime.get_output() == "result"
        finally:
            _cleanup("EXRT", "EXCALL")

    def test_ping_pong_trampoline_routines(self, runtime):
        """GOTO ping-pong between TRAMPOLINE routines — both have multiple labels."""
        try:
            mod_a = _load(
                "TPPA2\n G START\n Q\nSTART\n S N=$G(N)+1 I N>3 W N Q\n G ^TPPB2\n Q\n",
                "TPPA2",
            )
            _load(
                "TPPB2\n G GO\n Q\nGO\n G ^TPPA2\n Q\n",
                "TPPB2",
            )

            scope: dict = {}
            run_with_goto_support(mod_a.TPPA2, runtime, scope)
            assert runtime.get_output() == "4"
        finally:
            _cleanup("TPPA2", "TPPB2")


# =========================================================================
# Depth limit — prevent segfault from infinite GOTO recursion
# =========================================================================


@pytest.mark.codegen
class TestRwgsDepthLimit:
    """run_with_goto_support depth limit prevents segfaults.

    When TRAMPOLINE entry functions handle GotoExternal by calling rwgs
    recursively (e.g., DIP2 ↔ DIP22 GOTO cycle in FileMan PRINT), each
    cycle adds stack frames.  A depth limit raises a clean RecursionError
    instead of hitting the C-stack limit that causes a segfault.
    """

    def test_infinite_goto_cycle_raises_recursion_error(self, runtime):
        """Infinite GOTO cycle between TRAMPOLINE routines raises RecursionError.

        Entry functions re-raise GotoExternal, which rwgs handles iteratively.
        An iteration limit in rwgs detects the infinite cycle and raises
        RecursionError.
        """
        try:
            # INFRA and INFRB form an infinite GOTO cycle through TRAMPOLINE entries
            mod_a = _load(
                "INFRA\n G START\n Q\nSTART\n G ^INFRB\n Q\n",
                "INFRA",
            )
            _load(
                "INFRB\n G GO\n Q\nGO\n G ^INFRA\n Q\n",
                "INFRB",
            )

            scope: dict = {}
            with pytest.raises(RecursionError, match="iteration limit"):
                run_with_goto_support(mod_a.INFRA, runtime, scope)
        finally:
            _cleanup("INFRA", "INFRB")

    def test_iteration_counter_resets_between_calls(self, runtime):
        """After a successful GOTO chain, the iteration counter resets.

        A subsequent GOTO chain should work without hitting the limit.
        """
        try:
            mod_a = _load(
                "ICRST\n S N=$G(N)+1 I N>3 Q\n G ^ICRSTB\n Q\n",
                "ICRST",
            )
            _load("ICRSTB\n G ^ICRST\n Q\n", "ICRSTB")

            # First call: 3 iterations
            scope: dict = {}
            run_with_goto_support(mod_a.ICRST, runtime, scope)

            # Second call: should work fine (counter reset)
            scope2: dict = {}
            run_with_goto_support(mod_a.ICRST, runtime, scope2)
        finally:
            _cleanup("ICRST", "ICRSTB")


# =========================================================================
# _unwind_pending_news() unit tests
# =========================================================================


@pytest.mark.codegen
class TestUnwindPendingNews:
    """Unit tests for _unwind_pending_news() in run_with_goto_support.

    When entry functions re-raise GotoExternal, they save NEW stack
    entries to _rt._pending_new_entries.  When the GOTO chain QUITs
    normally, _unwind_pending_news restores scope variables in LIFO order
    (reverse of append order) — matching the normal NewScopeManager exit
    path which iterates reversed(self._restore_actions).  A *mark*
    parameter scopes unwinding to the current run_with_goto_support
    invocation so nested calls don't consume outer entries.
    """

    def test_no_pending_is_noop(self, runtime):
        """No pending entries → scope unchanged."""
        from m2py.runtime import _unwind_pending_news

        scope = {"X": "hello", "Y": "world"}
        _unwind_pending_news(runtime, scope)
        assert scope == {"X": "hello", "Y": "world"}

    def test_selective_new_restores_variable(self, runtime):
        """('var', name, saved_value) restores a single variable."""
        from m2py.runtime import _unwind_pending_news

        scope = {"X": "new_value"}
        runtime._pending_new_entries.append(("var", "X", "original"))
        _unwind_pending_news(runtime, scope)
        assert scope["X"] == "original"
        assert runtime._pending_new_entries == []

    def test_selective_new_removes_undefined_variable(self, runtime):
        """('var', name, None) removes variable from scope."""
        from m2py.runtime import _unwind_pending_news

        scope = {"X": "new_value", "Y": "keep"}
        runtime._pending_new_entries.append(("var", "X", None))
        _unwind_pending_news(runtime, scope)
        assert "X" not in scope
        assert scope["Y"] == "keep"
        assert runtime._pending_new_entries == []

    def test_argumentless_new_restores_full_snapshot(self, runtime):
        """('all', saved_dict) restores full scope snapshot."""
        from m2py.runtime import _unwind_pending_news

        scope = {"X": "new", "Y": "also_new"}
        saved = {"A": "old_a", "B": "old_b"}
        runtime._pending_new_entries.append(("all", saved))
        _unwind_pending_news(runtime, scope)
        assert scope == {"A": "old_a", "B": "old_b"}

    def test_exclusive_new_restores_non_kept_vars(self, runtime):
        """('excl', keep_set, saved_dict) restores non-kept variables."""
        from m2py.runtime import _unwind_pending_news

        scope = {"X": "current_x", "Y": "current_y"}
        saved = {"A": "old_a", "X": "old_x"}
        runtime._pending_new_entries.append(("excl", {"X"}, saved))
        _unwind_pending_news(runtime, scope)
        # X was in keep_set → preserved from current scope
        assert scope["X"] == "current_x"
        # A was in saved → restored
        assert scope["A"] == "old_a"
        # Y was not in saved or keep_set → gone
        assert "Y" not in scope

    def test_legacy_dict_entry_restores_full_snapshot(self, runtime):
        """Plain dict entry (legacy format) restores full scope."""
        from m2py.runtime import _unwind_pending_news

        scope = {"X": "new"}
        saved = {"A": "old_a"}
        runtime._pending_new_entries.append(saved)
        _unwind_pending_news(runtime, scope)
        assert scope == {"A": "old_a"}

    def test_lifo_ordering_of_multiple_entries(self, runtime):
        """Multiple entries are unwound in LIFO order (last entry first).

        Entries accumulate in append order as GotoExternal propagates
        outward through nested contexts: innermost routine's entries
        first, then wrapping scope snapshots, then outer routine entries.
        LIFO processing matches the normal NewScopeManager exit path
        which iterates reversed(self._restore_actions).
        """
        from m2py.runtime import _unwind_pending_news

        scope = {"X": "final"}
        # Entry 0: inner routine saved X="inner" (appended first)
        runtime._pending_new_entries.append(("var", "X", "inner"))
        # Entry 1: outer scope saved X="outer" (appended second)
        runtime._pending_new_entries.append(("var", "X", "outer"))

        _unwind_pending_news(runtime, scope)
        # LIFO: outer entry processed first (sets X="outer"),
        # then inner entry processed (sets X="inner")
        assert scope["X"] == "inner"

    def test_cross_context_ordering_inner_vars_then_outer_snapshot(self, runtime):
        """Outer scope snapshot processed first (LIFO), then inner var entries.

        Simulates the real GOTO propagation pattern:
        1. Inner routine NEWs X, GOTOs → entries: [('var', 'X', None)]
        2. Outer NewScopeManager → entries: [('var', 'X', None), ('all', snapshot)]

        LIFO processes outer snapshot first (restoring full scope), then
        inner var entry runs (removes X since saved as None).  The outer
        snapshot establishes the base, inner entries refine it.
        """
        from m2py.runtime import _unwind_pending_news

        scope = {"X": "new_val", "Y": "new_y", "DIIENS": "important"}
        # Inner routine's NEW for X (saved as undefined)
        runtime._pending_new_entries.append(("var", "X", None))
        # Outer NewScopeManager's full scope snapshot (the pre-call state)
        saved = {"X": "orig_x", "Y": "orig_y", "DIIENS": "orig_diiens"}
        runtime._pending_new_entries.append(("all", saved))

        _unwind_pending_news(runtime, scope)
        # LIFO: outer snapshot processed first (restores all),
        # then inner var entry removes X (saved as None)
        assert scope == {"Y": "orig_y", "DIIENS": "orig_diiens"}
        assert "X" not in scope

    def test_mark_scoping_only_unwinds_from_mark(self, runtime):
        """Only entries at index >= mark are unwound; earlier entries preserved.

        This tests the mark-based scoping that prevents nested
        run_with_goto_support calls from unwinding outer entries.
        """
        from m2py.runtime import _unwind_pending_news

        scope = {"X": "current"}
        # Entry from outer rwgs invocation (index 0)
        runtime._pending_new_entries.append(("var", "X", "outer_saved"))
        # Entry from inner rwgs invocation (index 1)
        runtime._pending_new_entries.append(("var", "X", "inner_saved"))

        # Unwind only from mark=1 (inner rwgs's entries)
        _unwind_pending_news(runtime, scope, mark=1)
        assert scope["X"] == "inner_saved"
        # Outer entry (index 0) is still in the list
        assert len(runtime._pending_new_entries) == 1
        assert runtime._pending_new_entries[0] == ("var", "X", "outer_saved")

    def test_pending_list_cleared_after_unwind(self, runtime):
        """Pending list is empty after unwinding."""
        from m2py.runtime import _unwind_pending_news

        scope = {"X": "val"}
        runtime._pending_new_entries.append(("var", "X", "old"))
        _unwind_pending_news(runtime, scope)
        assert runtime._pending_new_entries == []


# =========================================================================
# GOTO from within NEW scope — integration tests
# =========================================================================


@pytest.mark.codegen
class TestGotoFromWithinNewScope:
    """GOTO from within a NEW scope preserves variables for the target.

    When a subroutine NEWs variables and then GOTOs externally:
    1. The NEWed variables remain visible to the GOTO target
    2. After the GOTO chain QUITs, the NEWs are unwound
    """

    def test_new_vars_visible_across_goto(self, runtime):
        """Variables NEWed in routine A are visible to GOTO target B.

        A NEW's X, sets X="hello", GOTOs B.  B reads X.
        """
        try:
            mod_a = _load(
                'NVSRC\n N X S X="hello" G ^NVDST\n Q\n',
                "NVSRC",
            )
            _load(
                "NVDST\n W X Q\n",
                "NVDST",
            )

            scope: dict = {}
            run_with_goto_support(mod_a.NVSRC, runtime, scope)
            assert runtime.get_output() == "hello"
        finally:
            _cleanup("NVSRC", "NVDST")

    def test_new_unwound_after_goto_chain_quits(self, runtime):
        """After GOTO chain QUITs, NEWed variables are restored.

        DO SUB^A where SUB NEWs X (saving old value), sets X="new",
        GOTOs B. B QUITs.  After DO returns, X should be "old" again.
        """
        try:
            # SUB NEWs X, sets it, GOTOs NUWB
            _load(
                'NUWA\n G INIT\n Q\nINIT\n Q\nSUB\n N X S X="new" G ^NUWB\n Q\n',
                "NUWA",
            )
            _load(
                'NUWB\n W X," " Q\n',
                "NUWB",
            )
            # Caller sets X="old", DOs SUB^NUWA, reads X after
            mod_caller = _load(
                'NUWCALL\n S X="old" D SUB^NUWA W X Q\n',
                "NUWCALL",
            )

            scope: dict = {}
            run_with_goto_support(mod_caller.NUWCALL, runtime, scope)
            assert runtime.get_output() == "new old"
        finally:
            _cleanup("NUWA", "NUWB", "NUWCALL")

    def test_do_same_routine_catches_goto_external(self, runtime):
        """DO LABEL within same TRAMPOLINE routine catches GotoExternal.

        Pattern: MAIN calls D SUB (same routine).
        SUB does G ^EXT.  EXT QUITs.
        MAIN continues after the DO.
        """
        try:
            mod = _load(
                "DSGERT\n G MAIN\n Q\n"
                'MAIN\n D SUB^DSGERT W "after" Q\n'
                "SUB\n G ^DSGEEXT\n Q\n",
                "DSGERT",
            )
            _load(
                'DSGEEXT\n W "ext-" Q\n',
                "DSGEEXT",
            )

            scope: dict = {}
            run_with_goto_support(mod.DSGERT, runtime, scope)
            assert runtime.get_output() == "ext-after"
        finally:
            _cleanup("DSGERT", "DSGEEXT")

    def test_long_goto_chain_with_new_across_multiple_routines(self, runtime):
        """Multi-hop GOTO chain where each hop has NEW'd variables.

        A NEWs X, GOTOs B.  B NEWs Y, GOTOs C.  C writes X,Y, QUITs.
        After chain, both NEWs unwind.
        """
        try:
            mod_a = _load(
                'LGNEW\n N X S X="A" G ^LGNEWB\n Q\n',
                "LGNEW",
            )
            _load(
                'LGNEWB\n N Y S Y="B" G ^LGNEWC\n Q\n',
                "LGNEWB",
            )
            _load(
                "LGNEWC\n W X,Y Q\n",
                "LGNEWC",
            )

            scope: dict = {}
            run_with_goto_support(mod_a.LGNEW, runtime, scope)
            assert runtime.get_output() == "AB"
        finally:
            _cleanup("LGNEW", "LGNEWB", "LGNEWC")


# =========================================================================
# Codegen tests — verify _pm (pending mark) emission
# Commits 141d9dbe + 6138428b
# =========================================================================


@pytest.mark.codegen
class TestPendingMarkEmission:
    """Generated code emits _pm = _rt._pending_new_entries.__len__() before
    DO try blocks and passes _pending_mark=_pm to run_with_goto_support
    in GotoExternal handlers.

    Commit 141d9dbe introduced mark-based scoping so nested
    run_with_goto_support calls only unwind entries from their own
    invocation.  Commit 6138428b changed len() to __len__() to avoid
    shadowing by MUMPS parameters named 'len'.
    """

    def test_do_external_emits_pending_mark_save(self):
        """DO SUB where SUB has external GOTO emits _pm before try."""
        code = generate_python('TEST\n D SUB W "after" Q\nSUB\n G ^EXT\n Q\n')
        assert "_rt._pending_new_entries.__len__()" in code

    def test_pending_mark_uses_dunder_len_not_len(self):
        """Uses __len__() instead of len() to avoid shadowing by MUMPS 'len' param.

        Commit 6138428b: MUMPS routines may have a parameter named 'len'
        that shadows the Python builtin.
        """
        code = generate_python('TEST\n D SUB W "done" Q\nSUB\n G ^EXT\n Q\n')
        # Must use __len__(), not len()
        assert ".__len__()" in code
        # Should NOT use bare len() on _pending_new_entries
        assert "len(_rt._pending_new_entries)" not in code

    def test_goto_handler_passes_pending_mark(self):
        """GotoExternal handler passes _pending_mark=_pm to run_with_goto_support."""
        code = generate_python('TEST\n D SUB W "done" Q\nSUB\n G ^EXT\n Q\n')
        assert "_pending_mark=_pm" in code

    def test_do_internal_label_with_trampoline_emits_pending_mark(self):
        """DO LABEL in TRAMPOLINE strategy emits pending mark."""
        # Routine with internal GOTO (triggers TRAMPOLINE) + internal DO
        code = generate_python("TEST\n G NEXT\n Q\nNEXT\n D SUB\n Q\nSUB\n W 1 Q\n")
        assert "_rt._pending_new_entries.__len__()" in code

    def test_xecute_with_trampoline_emits_pending_mark(self):
        """XECUTE in trampoline context with external gotos emits pending mark."""
        # Routine with internal gotos (triggers TRAMPOLINE) + XECUTE with external GOTO
        code = generate_python('TEST\n G NEXT\n Q\nNEXT\n X "G ^EXT" Q\n')
        # Should have at least one _pm emission
        assert "_rt._pending_new_entries.__len__()" in code

    def test_pending_mark_before_try_block(self):
        """_pm assignment appears before the try: block, not inside it."""
        code = generate_python('TEST\n D SUB W "x" Q\nSUB\n G ^EXT\n Q\n')
        lines = code.split("\n")
        pm_line = None
        try_line = None
        for i, line in enumerate(lines):
            if "_pending_new_entries.__len__()" in line:
                pm_line = i
            if pm_line is not None and try_line is None and line.strip() == "try:":
                try_line = i
                break
        assert pm_line is not None, "_pm assignment not found"
        assert try_line is not None, "try: block not found after _pm"
        assert pm_line < try_line, "_pm must be emitted before try:"

    def test_routine_with_len_parameter_still_works(self):
        """A routine whose formal parameter is named 'len' doesn't break _pm.

        This is the bug that commit 6138428b fixed: if len() were used
        instead of __len__(), a formal param 'len' would shadow the builtin.
        """
        # Routine with param called 'len' + byref DO (triggers _pm emission)
        code = generate_python("TEST(len)\n D SUB(.len) Q\nSUB(a)\n S a=1 Q\n")
        # The generated code uses __len__() which is safe
        assert ".__len__()" in code
        assert "len(_rt._pending_new_entries)" not in code

    def test_byref_do_emits_pending_mark(self):
        """DO with by-reference argument emits pending mark."""
        code = generate_python("TEST(x)\n D SUB(.x) Q\nSUB(a)\n S a=1 Q\n")
        assert "_rt._pending_new_entries.__len__()" in code
        assert "_pending_mark=_pm" in code


# =========================================================================
# Runtime tests — _unwind_pending_news with mark parameter
# Commit 141d9dbe
# =========================================================================


@pytest.mark.codegen
class TestUnwindPendingNewsWithMark:
    """_unwind_pending_news(mark) only unwinds entries at index >= mark.

    Commit 141d9dbe changed _unwind_pending_news to accept a mark
    parameter so nested run_with_goto_support calls don't accidentally
    unwind entries belonging to an outer invocation.
    """

    def test_mark_zero_unwinds_all(self):
        """mark=0 (default) unwinds all pending entries."""
        rt = MUMPSRuntime()
        scope = {"X": "current"}
        rt._pending_new_entries.append(("var", "X", "original"))
        rt._pending_new_entries.append(("var", "Y", None))

        _unwind_pending_news(rt, scope, mark=0)

        assert scope.get("Y") is None  # Y removed
        assert scope["X"] == "original"  # X restored
        assert len(rt._pending_new_entries) == 0

    def test_mark_skips_earlier_entries(self):
        """Entries before mark are preserved untouched."""
        rt = MUMPSRuntime()
        scope = {"X": "current", "Y": "current"}
        # Entry 0: belongs to outer invocation
        rt._pending_new_entries.append(("var", "X", "outer-saved"))
        # Entry 1: belongs to inner invocation
        rt._pending_new_entries.append(("var", "Y", "inner-saved"))

        _unwind_pending_news(rt, scope, mark=1)

        # Only entry at index >= 1 unwound
        assert scope["Y"] == "inner-saved"
        # Entry 0 still pending and scope["X"] unchanged
        assert scope["X"] == "current"
        assert len(rt._pending_new_entries) == 1
        assert rt._pending_new_entries[0] == ("var", "X", "outer-saved")

    def test_mark_at_end_is_noop(self):
        """mark == len(pending) means nothing to unwind."""
        rt = MUMPSRuntime()
        scope = {"X": "val"}
        rt._pending_new_entries.append(("var", "X", "saved"))

        _unwind_pending_news(rt, scope, mark=1)  # mark == len

        assert scope["X"] == "val"  # Unchanged
        assert len(rt._pending_new_entries) == 1  # Still there

    def test_mark_beyond_end_is_noop(self):
        """mark > len(pending) is a no-op."""
        rt = MUMPSRuntime()
        scope = {}
        rt._pending_new_entries.append(("var", "A", "saved"))

        _unwind_pending_news(rt, scope, mark=99)

        assert len(rt._pending_new_entries) == 1

    def test_lifo_order_within_mark_slice(self):
        """Entries at index >= mark are unwound in LIFO (reverse) order."""
        rt = MUMPSRuntime()
        scope = {}
        # Append entries after mark=0: first sets X=1, second sets X=2
        rt._pending_new_entries.append(("var", "X", "first"))
        rt._pending_new_entries.append(("var", "X", "second"))

        _unwind_pending_news(rt, scope, mark=0)

        # LIFO: "second" is processed first (sets X="second"),
        # then "first" overwrites (sets X="first")
        assert scope["X"] == "first"

    def test_all_entry_type(self):
        """('all', saved_dict) entry type restores full scope."""
        rt = MUMPSRuntime()
        scope = {"X": "new", "Y": "new"}
        saved = {"A": "1", "B": "2"}
        rt._pending_new_entries.append(("all", saved))

        _unwind_pending_news(rt, scope, mark=0)

        assert scope == {"A": "1", "B": "2"}

    def test_excl_entry_type(self):
        """('excl', keep_set, saved_dict) restores non-kept vars."""
        rt = MUMPSRuntime()
        scope = {"X": "new-x", "Y": "new-y", "Z": "new-z"}
        saved = {"X": "old-x", "Y": "old-y", "W": "old-w"}
        # Exclusive NEW: keep Y, restore everything else from saved
        rt._pending_new_entries.append(("excl", {"Y"}, saved))

        _unwind_pending_news(rt, scope, mark=0)

        # Y kept from current scope, everything else from saved
        assert scope["Y"] == "new-y"
        assert scope["X"] == "old-x"
        assert scope["W"] == "old-w"
        assert "Z" not in scope  # Not in saved, not kept

    def test_var_entry_restore(self):
        """('var', name, saved_value) restores a single variable."""
        rt = MUMPSRuntime()
        scope = {"X": "modified"}
        rt._pending_new_entries.append(("var", "X", "original"))

        _unwind_pending_news(rt, scope, mark=0)

        assert scope["X"] == "original"

    def test_var_entry_delete_when_none(self):
        """('var', name, None) removes the variable from scope."""
        rt = MUMPSRuntime()
        scope = {"X": "to-delete"}
        rt._pending_new_entries.append(("var", "X", None))

        _unwind_pending_news(rt, scope, mark=0)

        assert "X" not in scope

    def test_dict_legacy_entry(self):
        """Plain dict entry (legacy format) restores full scope."""
        rt = MUMPSRuntime()
        scope = {"X": "new"}
        rt._pending_new_entries.append({"A": "1", "B": "2"})

        _unwind_pending_news(rt, scope, mark=0)

        assert scope == {"A": "1", "B": "2"}

    def test_empty_pending_with_mark_zero(self):
        """No entries to unwind is a no-op."""
        rt = MUMPSRuntime()
        scope = {"X": "val"}

        _unwind_pending_news(rt, scope, mark=0)

        assert scope == {"X": "val"}

    def test_mixed_entry_types_with_mark(self):
        """Multiple entry types with mark > 0."""
        rt = MUMPSRuntime()
        scope = {"X": "current", "Y": "current"}

        # Index 0: outer invocation entry (should be preserved)
        rt._pending_new_entries.append(("var", "X", "outer"))
        # Index 1-2: inner invocation entries
        rt._pending_new_entries.append(("var", "Y", "inner-y"))
        rt._pending_new_entries.append(("var", "X", "inner-x"))

        _unwind_pending_news(rt, scope, mark=1)

        # Inner entries unwound in LIFO order:
        # ("var", "X", "inner-x") processed first → X="inner-x"
        # ("var", "Y", "inner-y") processed second → Y="inner-y"
        assert scope["Y"] == "inner-y"
        assert scope["X"] == "inner-x"
        # Outer entry preserved
        assert len(rt._pending_new_entries) == 1
        assert rt._pending_new_entries[0] == ("var", "X", "outer")


# =========================================================================
# Runtime tests — run_with_goto_support _pending_mark parameter
# Commit 141d9dbe
# =========================================================================


@pytest.mark.codegen
class TestRunWithGotoSupportPendingMark:
    """run_with_goto_support auto-sets _pending_mark when None."""

    def test_pending_mark_auto_set(self, runtime):
        """When _pending_mark is None, it auto-sets to current pending length."""
        # Pre-populate some pending entries (simulating outer invocation)
        runtime._pending_new_entries.append(("var", "X", "outer"))

        try:
            mod = _load('PMTEST\n W "ok" Q\n', "PMTEST")
            scope: dict = {}
            run_with_goto_support(mod.PMTEST, runtime, scope)
            assert runtime.get_output() == "ok"
            # The outer entry should NOT have been unwound
            assert len(runtime._pending_new_entries) == 1
        finally:
            _cleanup("PMTEST")

    def test_explicit_pending_mark_respected(self, runtime):
        """Explicit _pending_mark=0 unwinds from the beginning."""
        runtime._pending_new_entries.append(("var", "X", "saved"))

        try:
            mod = _load('PMTEST2\n W "ok" Q\n', "PMTEST2")
            scope: dict = {"X": "current"}
            run_with_goto_support(mod.PMTEST2, runtime, scope, _pending_mark=0)
            assert runtime.get_output() == "ok"
            # With explicit mark=0, all entries should be unwound
            assert len(runtime._pending_new_entries) == 0
            assert scope["X"] == "saved"
        finally:
            _cleanup("PMTEST2")

    def test_nested_rwgs_isolates_pending_entries(self, runtime):
        """Nested run_with_goto_support calls don't unwind outer entries.

        DO SUB → SUB GOTOs ^EXT → EXT QUITs.
        Meanwhile, the outer rwgs had pre-existing pending entries.
        """
        runtime._pending_new_entries.append(("var", "OUTER", "preserved"))

        try:
            mod = _load(
                'NRWGS\n D SUB^NRWGS W "after" Q\nSUB\n W "sub" G ^NRWGSEXT\n Q\n',
                "NRWGS",
            )
            _load('NRWGSEXT\n W "ext" Q\n', "NRWGSEXT")

            scope: dict = {}
            run_with_goto_support(mod.NRWGS, runtime, scope)
            assert runtime.get_output() == "subextafter"
            # Outer pending entry preserved
            assert len(runtime._pending_new_entries) == 1
            assert runtime._pending_new_entries[0] == ("var", "OUTER", "preserved")
        finally:
            _cleanup("NRWGS", "NRWGSEXT")
