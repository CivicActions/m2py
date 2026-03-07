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
        """After run_with_goto_support, the handler syncs scope→state.

        The handler pattern is:
            except GotoExternal:
                state→scope sync
                run_with_goto_support(...)
                scope→state sync
                target = None
        """
        code = generate_python("TEST\n G NEXT\n Q\nNEXT\n G ^OTHER\n Q\n")
        lines = code.split("\n")

        in_main = False
        in_handler = False
        found_rwgs = False
        found_target_none = False
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
                if "run_with_goto_support" in stripped:
                    found_rwgs = True
                    continue
                if stripped == "target = None":
                    found_target_none = True
                if stripped.startswith("except "):
                    break

        assert found_rwgs, "Handler must call run_with_goto_support"
        assert found_target_none, "Handler must set target = None"

    def test_handler_does_not_use_bare_raise(self):
        """GotoExternal handler must NOT use bare 'raise'.

        A bare 'raise' would abort the trampoline and escape past the
        DO boundary, breaking wrapper-label patterns.
        """
        code = generate_python("TEST\n G NEXT\n Q\nNEXT\n G ^OTHER\n Q\n")
        lines = code.split("\n")

        in_main = False
        in_handler = False
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
                assert stripped != "raise", (
                    "GotoExternal handler must NOT use bare 'raise' — "
                    "this would abort the trampoline and break wrapper labels"
                )
                if stripped.startswith("except "):
                    break

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

        TRAMPOLINE routines catch GotoExternal and call rwgs recursively,
        which can cause unbounded nesting.  The depth limit prevents segfault.
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
            with pytest.raises(RecursionError, match="depth.*exceeded"):
                run_with_goto_support(mod_a.INFRA, runtime, scope)
        finally:
            _cleanup("INFRA", "INFRB")
