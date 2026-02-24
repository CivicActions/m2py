"""Tests for MERGE command in TRAMPOLINE-strategy routines.

Bug L: MERGE codegen in TRAMPOLINE strategy generated bare Python variable
names (e.g., ``ERR``, ``LVL``) instead of accessing them through
``state._locals[...]``.  This caused NameError at runtime because TRAMPOLINE
inner functions only access local variables through the state object or
``_scope`` dict, not as bare Python names.

Real-world case: MXMLPRS0 (VistA XML Parser) state 3 has ``M LVL(LVL)=ERR``
which should merge the ERR array into LVL(LVL).  Before the fix, the
generated code was ``_merge_src = ERR`` (NameError) instead of
``_merge_src = state._locals.get('ERR', MArray())``.
"""

import pytest

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


@pytest.mark.codegen
class TestTrampolineMerge:
    """MERGE command in TRAMPOLINE-strategy routines."""

    @pytest.fixture
    def execute_mumps(self):
        def _execute(source: str):
            python_code = generate_python(source)
            runtime = MUMPSRuntime()
            return runtime.execute(python_code, capture_output=True)

        return _execute

    def test_merge_local_to_local_trampoline(self, execute_mumps):
        """M B=A in routine with GOTO (forces TRAMPOLINE)."""
        source = (
            "TEST\n"
            " S A(1)=10,A(2)=20\n"
            " M B=A\n"
            ' W B(1)," ",B(2),!\n'
            " GOTO END\n"
            " QUIT\n"
            "END\n"
            ' W "done",!\n'
            " QUIT\n"
        )
        result = execute_mumps(source)
        assert result.output == "10 20\ndone\n"

    def test_merge_subscripted_dest_trampoline(self, execute_mumps):
        """M B(1)=A — merge A tree into B(1) subtree."""
        source = (
            "TEST\n"
            ' S A(1)="x",A(2)="y"\n'
            " M B(1)=A\n"
            ' W B(1,1)," ",B(1,2),!\n'
            " GOTO END\n"
            " QUIT\n"
            "END\n"
            ' W "done",!\n'
            " QUIT\n"
        )
        result = execute_mumps(source)
        assert result.output == "x y\ndone\n"

    def test_merge_subscripted_source_trampoline(self, execute_mumps):
        """M B=A(1) — merge subtree of A rooted at A(1)."""
        source = (
            "TEST\n"
            ' S A(1,"a")=10,A(1,"b")=20\n'
            " M B=A(1)\n"
            ' W B("a")," ",B("b"),!\n'
            " GOTO END\n"
            " QUIT\n"
            "END\n"
            ' W "done",!\n'
            " QUIT\n"
        )
        result = execute_mumps(source)
        assert result.output == "10 20\ndone\n"

    def test_merge_in_state_function_trampoline(self, execute_mumps):
        """MERGE inside a label reached by GOTO (deeper TRAMPOLINE state).

        This replicates the MXMLPRS0 pattern where MERGE is inside
        a state that is executed via trampoline dispatch.
        """
        source = (
            "TEST\n"
            ' S ERR("SEV")=1,ERR("MSG")="test"\n'
            " S LVL=1\n"
            " GOTO PROC\n"
            " QUIT\n"
            "PROC\n"
            " M LVL(LVL)=ERR\n"
            ' W LVL(1,"SEV")," ",LVL(1,"MSG"),!\n'
            " GOTO END\n"
            " QUIT\n"
            "END\n"
            ' W "done",!\n'
            " QUIT\n"
        )
        result = execute_mumps(source)
        assert result.output == "1 test\ndone\n"
