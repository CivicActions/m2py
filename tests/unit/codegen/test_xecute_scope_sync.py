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
