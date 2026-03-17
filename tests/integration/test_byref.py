"""Tests for by-reference parameter passing (MArray aliasing).

Verifies that by-reference parameter passing uses MArray aliasing
(DATA-CELL semantics per MUMPS 8.1.7) under both SIMPLE_FUNCTIONS
and TRAMPOLINE codegen strategies.

Key behaviors tested:
- Basic by-ref mutation visible to caller
- Multiple by-ref params
- Descendant modification visibility (SET Y(1)="sub" where Y is by-ref)
- $DATA reflection through by-ref alias
- Error-case mutation preservation
- Unmodified by-ref param (no overhead or behavioral change)
"""

import pytest

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


@pytest.mark.codegen
class TestByRefSimpleFunctions:
    """By-ref under SIMPLE_FUNCTIONS strategy (no GOTOs)."""

    @pytest.fixture
    def execute_mumps(self):
        def _execute(source: str):
            python_code = generate_python(source)
            runtime = MUMPSRuntime()
            return runtime.execute(python_code, capture_output=True)

        return _execute

    def test_basic_byref_mutation(self, execute_mumps):
        """Basic by-ref: callee sets Y=42, caller sees X=42."""
        source = (
            "TEST\n SET X=1\n DO SUB(.X)\n WRITE X,!\n QUIT\nSUB(Y) SET Y=42\n QUIT\n"
        )
        result = execute_mumps(source)
        assert result.output == "42\n"

    def test_multiple_byref_params(self, execute_mumps):
        """Multiple by-ref params: all modified values visible to caller."""
        source = (
            "TEST\n"
            " SET A=1,B=2\n"
            " DO SWAP(.A,.B)\n"
            ' WRITE A,",",B,!\n'
            " QUIT\n"
            "SWAP(X,Y) NEW T SET T=X,X=Y,Y=T\n"
            " QUIT\n"
        )
        result = execute_mumps(source)
        assert result.output == "2,1\n"

    def test_byref_descendant_visibility(self, execute_mumps):
        """SET Y(1)='sub' through by-ref is visible as X(1) in caller."""
        source = (
            "TEST\n"
            " SET X=1\n"
            " DO SUB(.X)\n"
            " WRITE X,!\n"
            " WRITE X(1),!\n"
            " QUIT\n"
            "SUB(Y)\n"
            " SET Y=100\n"
            ' SET Y(1)="sub"\n'
            " QUIT\n"
        )
        result = execute_mumps(source)
        assert result.output == "100\nsub\n"

    def test_byref_data_reflection(self, execute_mumps):
        """$DATA through by-ref alias reflects modifications."""
        source = (
            "TEST\n"
            " SET X=1\n"
            " DO SUB(.X)\n"
            " WRITE $DATA(X),!\n"
            " QUIT\n"
            "SUB(Y)\n"
            " SET Y=100\n"
            ' SET Y(1)="sub"\n'
            " QUIT\n"
        )
        result = execute_mumps(source)
        # $DATA=11 means node has both value and descendants
        assert result.output == "11\n"

    def test_byref_unmodified_param(self, execute_mumps):
        """Unmodified by-ref param: value stays the same."""
        source = "TEST\n SET X=42\n DO NOOP(.X)\n WRITE X,!\n QUIT\nNOOP(Y)\n QUIT\n"
        result = execute_mumps(source)
        assert result.output == "42\n"

    def test_byref_undefined_to_defined(self, execute_mumps):
        """By-ref on undefined variable: callee sets it, caller sees it."""
        source = "TEST\n DO SUB(.X)\n WRITE X,!\n QUIT\nSUB(Y) SET Y=99\n QUIT\n"
        result = execute_mumps(source)
        assert result.output == "99\n"


@pytest.mark.codegen
class TestByRefTrampoline:
    """By-ref under TRAMPOLINE strategy (requires GOTOs to trigger it).

    These routines use inter-label GOTOs to force TRAMPOLINE strategy selection.
    """

    @pytest.fixture
    def execute_mumps(self):
        def _execute(source: str):
            python_code = generate_python(source)
            runtime = MUMPSRuntime()
            return runtime.execute(python_code, capture_output=True)

        return _execute

    def test_basic_byref_with_goto(self, execute_mumps):
        """By-ref in a TRAMPOLINE routine: basic mutation."""
        source = (
            "TEST\n"
            " SET X=1\n"
            " DO SUB(.X)\n"
            " WRITE X,!\n"
            " GOTO END\n"
            "SUB(Y) SET Y=42\n"
            " QUIT\n"
            "END QUIT\n"
        )
        result = execute_mumps(source)
        assert result.output == "42\n"

    def test_multiple_byref_with_goto(self, execute_mumps):
        """Multiple by-ref params in TRAMPOLINE routine."""
        source = (
            "TEST\n"
            " SET A=1,B=2\n"
            " DO SWAP(.A,.B)\n"
            ' WRITE A,",",B,!\n'
            " GOTO END\n"
            "SWAP(X,Y) NEW T SET T=X,X=Y,Y=T\n"
            " QUIT\n"
            "END QUIT\n"
        )
        result = execute_mumps(source)
        assert result.output == "2,1\n"

    def test_byref_descendant_with_goto(self, execute_mumps):
        """Descendant modification through by-ref under TRAMPOLINE."""
        source = (
            "TEST\n"
            " SET X=1\n"
            " DO SUB(.X)\n"
            " WRITE X,!\n"
            " WRITE X(1),!\n"
            " GOTO END\n"
            "SUB(Y)\n"
            " SET Y=100\n"
            ' SET Y(1)="sub"\n'
            " QUIT\n"
            "END QUIT\n"
        )
        result = execute_mumps(source)
        assert result.output == "100\nsub\n"

    def test_byref_data_with_goto(self, execute_mumps):
        """$DATA reflection through by-ref under TRAMPOLINE."""
        source = (
            "TEST\n"
            " SET X=1\n"
            " DO SUB(.X)\n"
            " WRITE $DATA(X),!\n"
            " GOTO END\n"
            "SUB(Y)\n"
            " SET Y=100\n"
            ' SET Y(1)="sub"\n'
            " QUIT\n"
            "END QUIT\n"
        )
        result = execute_mumps(source)
        # $DATA=11 means node has both value and descendants
        assert result.output == "11\n"

    def test_byref_unmodified_with_goto(self, execute_mumps):
        """Unmodified by-ref in TRAMPOLINE: value preserved."""
        source = (
            "TEST\n"
            " SET X=42\n"
            " DO NOOP(.X)\n"
            " WRITE X,!\n"
            " GOTO END\n"
            "NOOP(Y)\n"
            " QUIT\n"
            "END QUIT\n"
        )
        result = execute_mumps(source)
        assert result.output == "42\n"


@pytest.mark.codegen
class TestByRefCrossStrategy:
    """Tests verifying both strategies produce identical results."""

    @pytest.fixture
    def execute_mumps(self):
        def _execute(source: str):
            python_code = generate_python(source)
            runtime = MUMPSRuntime()
            return runtime.execute(python_code, capture_output=True)

        return _execute

    def test_increment_via_byref(self, execute_mumps):
        """Increment by-ref parameter: D INCR(.X)."""
        source = (
            "TEST\n"
            " SET X=10\n"
            " DO INCR(.X)\n"
            " WRITE X,!\n"
            " QUIT\n"
            "INCR(V) SET V=V+1\n"
            " QUIT\n"
        )
        result = execute_mumps(source)
        assert result.output == "11\n"

    def test_byref_with_mixed_params(self, execute_mumps):
        """Mixed by-ref and by-value params in same call."""
        source = (
            "TEST\n"
            " SET X=5\n"
            " DO ADD(.X,10)\n"
            " WRITE X,!\n"
            " QUIT\n"
            "ADD(R,V) SET R=R+V\n"
            " QUIT\n"
        )
        result = execute_mumps(source)
        assert result.output == "15\n"

    def test_byref_kill_visibility(self, execute_mumps):
        """KILL on by-ref param visible to caller via $DATA."""
        source = (
            "TEST\n"
            " SET X=1\n"
            " DO SUB(.X)\n"
            " WRITE $DATA(X),!\n"
            " QUIT\n"
            "SUB(Y)\n"
            ' SET Y(1)="child"\n'
            " KILL Y\n"
            " QUIT\n"
        )
        result = execute_mumps(source)
        # After KILL Y, $DATA(X) should be 0 (no value, no descendants)
        assert result.output == "0\n"

    def test_byref_percent_variable_extrinsic(self, execute_mumps):
        """Extrinsic call with %-prefixed variable passed by reference.

        Verifies that .%VAR byref arguments correctly resolve in scope
        when the variable name requires _pct_ encoding.
        """
        source = (
            "TEST ;\n"
            " N %1\n"
            ' S %1("type")="japaense"\n'
            ' S %1("origin")="japan"\n'
            ' W $$FN("name",.%1),!\n'
            " Q\n"
            "FN(NAME,ATTRS) ;\n"
            ' N I,S S S="",I=""\n'
            ' F  S I=$O(ATTRS(I)) Q:I=""  S S=S_" "_I_"="_ATTRS(I)\n'
            ' Q "<"_NAME_S_">"\n'
        )
        result = execute_mumps(source)
        assert result.output == "<name origin=japan type=japaense>\n"

    def test_byref_percent_variable_do_call(self, execute_mumps):
        """DO call with %-prefixed variable passed by reference.

        Verifies that .%VAR byref works for DO (non-extrinsic) calls too.
        """
        source = (
            "TEST ;\n"
            " N %A\n"
            ' S %A("x")=10,%A("y")=20\n'
            " D SUB(.%A)\n"
            ' W %A("sum"),!\n'
            " Q\n"
            "SUB(P) ;\n"
            ' S P("sum")=P("x")+P("y")\n'
            " Q\n"
        )
        result = execute_mumps(source)
        assert result.output == "30\n"

    def test_byref_with_omitted_args_positional(self, execute_mumps):
        """DO call with omitted args + byref preserves positional mapping.

        MUMPS: D START("Books",,"G",,.%1) — args 2 and 4 are omitted.
        Verifies that None placeholders are generated for omitted args
        so that byref arg %1 lands at position 5 (ATT), not position 3.
        """
        source = (
            "TEST ;\n"
            ' N %1 S %1("ver")="2.5"\n'
            ' D START("Books",,"G",,.%1)\n'
            " W $G(^X(1)),!\n"
            " Q\n"
            "START(A,B,C,D,ATT) ;\n"
            " K ^X\n"
            ' S ^X("DOC")=A\n'
            ' I $G(C)["G" S ^X("CNT")=1\n'
            ' N V S V=$G(^X("CNT"))\n'
            ' I V S ^X(V)="first",^X("CNT")=V+1\n'
            " Q\n"
        )
        result = execute_mumps(source)
        assert result.output == "first\n"

    def test_extrinsic_label_variable_name_collision(self, execute_mumps):
        """Extrinsic call where label name matches a formal parameter.

        MUMPS allows $$ATT(.ATT) — calling label ATT while passing variable
        ATT by reference.  Labels and variables live in separate namespaces
        in MUMPS.  The generated code must use _globals['ATT'] to avoid the
        formal parameter shadowing the module-level function.
        """
        source = (
            "TEST ;\n"
            ' N ATT S ATT("x")="hello"\n'
            " W $$ATT(.ATT),!\n"
            " Q\n"
            "ATT(A) ;\n"
            ' Q $G(A("x"))_" world"\n'
        )
        result = execute_mumps(source)
        assert result.output == "hello world\n"

    def test_new_dedup_clears_subscripts(self, execute_mumps):
        """Repeated NEW at same scope level clears variable subscripts.

        In real MUMPS (YDB/GT.M), a second N %1 at the same stack level
        makes the variable undefined (clears subscripts) while keeping
        the original restore point.
        """
        source = (
            "TEST ;\n"
            ' N X S X("a")="1",X("b")="2"\n'
            " N X\n"
            ' S X("c")="3"\n'
            ' W $G(X("a")),":",$G(X("b")),":",X("c"),!\n'
            " Q\n"
        )
        result = execute_mumps(source)
        # After second NEW, X("a") and X("b") should be gone; only X("c") set
        assert result.output == "::3\n"
