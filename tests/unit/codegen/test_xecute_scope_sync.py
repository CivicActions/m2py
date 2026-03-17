"""Tests for XECUTE scope synchronization in TRAMPOLINE mode.

Verifies that variables set by XECUTE'd code are visible to subsequent
code in TRAMPOLINE-compiled routines (state._locals ← _scope reverse sync).

Bug context: XECUTE modifies _scope directly, but TRAMPOLINE code reads
from state._locals.  Without a reverse sync after execute_mumps(), changes
made by XECUTE'd code were invisible to the calling compiled function.
"""

from __future__ import annotations

import pytest

from m2py.runtime import MUMPSRuntime


@pytest.mark.codegen
class TestXecuteScopeSyncTrampoline:
    """XECUTE variable visibility in TRAMPOLINE compiled routines."""

    @pytest.fixture
    def rt(self):
        return MUMPSRuntime()

    def _compile_and_run(self, rt: MUMPSRuntime, mumps_code: str) -> str:
        """Compile MUMPS code as TRAMPOLINE routine, run it, return output."""
        generate = rt._get_codegen_callback()
        python_code = generate(mumps_code, routine_name="TEST")
        ns: dict = {}
        exec(compile(python_code, "<test>", "exec"), ns)
        scope: dict = {}
        rt._current_routine = "TEST"
        ns["TEST"](rt, _scope=scope)
        return rt.get_output()

    def test_xecute_sets_variable_visible_after(self, rt):
        """X set by XECUTE should be readable by subsequent W command."""
        code = 'TEST\n X "S X=42"\n W X\n Q'
        output = self._compile_and_run(rt, code)
        assert output == "42"

    def test_xecute_sets_variable_used_in_condition(self, rt):
        """Variable set by XECUTE should work in IF conditions."""
        code = 'TEST\n X "S OK=1"\n I OK W "yes"\n Q'
        output = self._compile_and_run(rt, code)
        assert output == "yes"

    def test_xecute_variable_survives_kill(self, rt):
        """KILL then XECUTE SET should make variable visible again."""
        code = 'TEST\n S X=1 K X X "S X=99"\n W X\n Q'
        output = self._compile_and_run(rt, code)
        assert output == "99"

    def test_xecute_sets_multiple_variables(self, rt):
        """Multiple variables set by XECUTE visible to caller."""
        code = 'TEST\n X "S A=1,B=2,C=3"\n W A+B+C\n Q'
        output = self._compile_and_run(rt, code)
        assert output == "6"

    def test_xecute_indirected_code(self, rt):
        """XECUTE of variable containing code sets vars visible to caller."""
        code = 'TEST\n S CMD="S RESULT=123" X CMD W RESULT\n Q'
        output = self._compile_and_run(rt, code)
        assert output == "123"

    def test_xecute_in_loop_accumulates(self, rt):
        """XECUTE inside FOR loop can accumulate into variables."""
        code = 'TEST\n S SUM=0 F I=1:1:3 X "S SUM=SUM+I"\n W SUM\n Q'
        output = self._compile_and_run(rt, code)
        assert output == "6"

    def test_xecute_sets_subscripted_variable(self, rt):
        """XECUTE setting subscripted variable visible in caller."""
        code = 'TEST\n X "S ARR(1)=""A"",ARR(2)=""B"""\n W ARR(1),ARR(2)\n Q'
        output = self._compile_and_run(rt, code)
        assert output == "AB"

    def test_xecute_within_subroutine(self, rt):
        """XECUTE in a called subroutine sets vars visible in that scope."""
        code = 'TEST\n D SUB\n Q\nSUB\n X "S X=777"\n W X\n Q'
        output = self._compile_and_run(rt, code)
        assert output == "777"

    def test_xecute_after_new(self, rt):
        """XECUTE after NEW: variable set by XECUTE visible in NEW scope."""
        code = (
            "TEST\n"
            " S X=1\n"
            " D SUB\n"
            ' W "after:",X\n'
            " Q\n"
            "SUB\n"
            " N X\n"
            ' X "S X=99"\n'
            ' W "sub:",X,","\n'
            " Q"
        )
        output = self._compile_and_run(rt, code)
        assert output == "sub:99,after:1"


@pytest.mark.codegen
class TestXecuteCallerVarsVisibleInDynamicXecute:
    """Variables set by the caller must be visible inside dynamic XECUTE.

    In MUMPS, XECUTE runs in the caller's scope — all local variables
    are accessible.  For TRAMPOLINE-compiled routines with static state
    fields, variables live as ``state.X`` while ``execute_mumps()``
    receives ``_scope``.  A state→scope sync before each dynamic XECUTE
    call is required so the XECUTE'd code sees current values.

    These tests use **dynamic** (non-constant) XECUTE to exercise the
    ``execute_mumps()`` code path.  Constant-string XECUTE is inlined
    at codegen time and doesn't go through scope sync.
    """

    @pytest.fixture
    def rt(self):
        return MUMPSRuntime()

    def _compile_and_run(self, rt: MUMPSRuntime, mumps_code: str) -> str:
        """Compile MUMPS code as TRAMPOLINE routine, run it, return output."""
        generate = rt._get_codegen_callback()
        python_code = generate(mumps_code, routine_name="TEST")
        ns: dict = {}
        exec(compile(python_code, "<test>", "exec"), ns)
        scope: dict = {}
        rt._current_routine = "TEST"
        ns["TEST"](rt, _scope=scope)
        return rt.get_output()

    def test_caller_scalar_visible_in_dynamic_xecute(self, rt):
        """Caller-set scalar X must be readable inside dynamic XECUTE."""
        code = 'TEST\n S X=42,CODE="W X" X CODE\n Q'
        output = self._compile_and_run(rt, code)
        assert output == "42"

    def test_caller_multiple_vars_visible(self, rt):
        """Multiple caller variables visible inside dynamic XECUTE."""
        code = 'TEST\n S A=10,B=20,CODE="W A+B" X CODE\n Q'
        output = self._compile_and_run(rt, code)
        assert output == "30"

    def test_caller_var_modified_by_dynamic_xecute(self, rt):
        """Caller var modified by dynamic XECUTE visible after return."""
        code = 'TEST\n S X=1,CODE="S X=99" X CODE W X\n Q'
        output = self._compile_and_run(rt, code)
        assert output == "99"

    def test_loop_var_visible_in_dynamic_xecute(self, rt):
        """FOR loop variable I visible inside dynamic XECUTE."""
        code = 'TEST\n S CODE="W I" F I=1:1:3 X CODE\n Q'
        output = self._compile_and_run(rt, code)
        assert output == "123"

    def test_accumulator_across_dynamic_xecute_loop(self, rt):
        """Accumulator pattern: caller SUM visible and modifiable in loop."""
        code = 'TEST\n S SUM=0,CODE="S SUM=SUM+I" F I=1:1:5 X CODE\n W SUM\n Q'
        output = self._compile_and_run(rt, code)
        assert output == "15"

    def test_subscripted_var_visible_in_dynamic_xecute(self, rt):
        """Subscripted array variable visible inside dynamic XECUTE."""
        code = 'TEST\n S ARR(1)="A",ARR(2)="B",CODE="W ARR(1),ARR(2)" X CODE\n Q'
        output = self._compile_and_run(rt, code)
        assert output == "AB"

    def test_nested_dynamic_xecute(self, rt):
        """Variable visible through nested dynamic XECUTE."""
        code = 'TEST\n S X=7,INNER="W X",OUTER="X INNER"\n X OUTER\n Q'
        output = self._compile_and_run(rt, code)
        assert output == "7"

    def test_var_updated_between_xecutes(self, rt):
        """Variable updated between two dynamic XECUTEs — second sees new value."""
        code = 'TEST\n S CODE="W X,!"\n S X=1 X CODE\n S X=2 X CODE\n Q'
        output = self._compile_and_run(rt, code)
        assert output == "1\n2\n"

    def test_dynamic_xecute_with_postcondition(self, rt):
        """Dynamic XECUTE with postcondition still sees caller vars."""
        code = 'TEST\n S X=1,FLAG=1,CODE="W X" X:FLAG CODE\n Q'
        output = self._compile_and_run(rt, code)
        assert output == "1"


@pytest.mark.codegen
class TestExecuteMumpsCallerGlobalsFilter:
    """Verify that execute_mumps() caller_globals filtering works correctly.

    The caller_globals loop in execute_mumps() must:
    - Allow translated label names starting with ``_`` (e.g. ``_a_O``,
      ``_pct_ut``) so XECUTE'd code can DO/GOTO those labels.
    - Block Python dunders (``__name__``, ``__builtins__``) to avoid
      polluting the exec namespace.
    - Let callables override same-named MArray entries from ``_scope``.

    Bug context: The old filter ``not name.startswith("_")`` blocked ALL
    underscore-prefixed names, preventing translated label functions like
    ``_a_O`` (label ``O``) from entering the namespace.  When _scope
    contained a same-named MArray (from state→scope sync), the MArray
    shadowed the callable → ``TypeError: 'MArray' object is not callable``.
    """

    @pytest.fixture
    def rt(self):
        return MUMPSRuntime()

    def test_underscore_prefixed_callable_in_caller_globals(self, rt):
        """Callable with _ prefix from caller_globals must be in namespace."""
        from m2py.runtime import MArray

        scope: dict = {}
        # Simulate a _scope that has an MArray with same name as a label
        scope["_a_O"] = MArray(value="should be overridden")

        def fake_label(rt, _scope=None):
            rt.write("called")

        caller_globals = {"_a_O": fake_label, "__name__": "test_module"}
        rt.execute_mumps('W "before"', scope, caller_globals)
        # The callable should have been available (no TypeError)
        output = rt.get_output()
        assert output == "before"

    def test_dunder_names_excluded_from_namespace(self, rt):
        """Python dunder names must NOT enter the exec namespace."""
        scope: dict = {}
        caller_globals = {
            "__name__": "bad_module",
            "__builtins__": {"print": print},
            "GOOD": lambda rt, _scope=None: None,
        }
        # This should not crash — dunders are filtered out
        rt.execute_mumps('W "ok"', scope, caller_globals)
        assert rt.get_output() == "ok"

    def test_callable_overrides_marray_in_scope(self, rt):
        """Callable from caller_globals must override MArray from _scope."""
        from m2py.runtime import MArray

        scope = {"_pct_X": MArray(value="marray_value")}

        called = []

        def pct_x_label(rt, _scope=None):
            called.append(True)
            rt.write("label_called")

        caller_globals = {"_pct_X": pct_x_label}
        # XECUTE code that calls _pct_X should get the callable, not the MArray
        rt.execute_mumps('W "hello"', scope, caller_globals)
        assert rt.get_output() == "hello"

    def test_xecute_do_to_label_in_caller_routine(self, rt):
        """XECUTE'd code must be able to DO a label from the calling routine.

        This is the DIO2 pattern: X DY(DN) where DY(DN) contains
        code like 'S DISTP=DISTP+1 D CSTP' — CSTP is a label in DIO2.
        """
        code = 'TEST\n S CODE="D SUB"\n X CODE\n Q\nSUB\n W "sub ran"\n Q'
        generate = rt._get_codegen_callback()
        python_code = generate(code, routine_name="TEST")
        ns: dict = {}
        exec(compile(python_code, "<test>", "exec"), ns)
        scope: dict = {}
        rt._current_routine = "TEST"
        ns["TEST"](rt, _scope=scope)
        assert rt.get_output() == "sub ran"

    def test_xecute_do_with_scope_var_same_name_as_label(self, rt):
        """Variable and label share a name: XECUTE DO should call label."""
        # In MUMPS, S is both a variable name and could be a label name.
        # D S always means DO label S, XECUTE "D S" should call label S.
        code = 'TEST\n S S=999\n S CODE="D S"\n X CODE\n Q\nS\n W S\n Q'
        generate = rt._get_codegen_callback()
        python_code = generate(code, routine_name="TEST")
        ns: dict = {}
        exec(compile(python_code, "<test>", "exec"), ns)
        scope: dict = {}
        rt._current_routine = "TEST"
        ns["TEST"](rt, _scope=scope)
        # Label S writes variable S's value (999)
        assert rt.get_output() == "999"
