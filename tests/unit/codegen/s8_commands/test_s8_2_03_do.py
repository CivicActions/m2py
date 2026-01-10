"""Tests for DO command code generation (§8.2.3).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.3
"""

import pytest


@pytest.mark.codegen
class TestDoCommandCodegen:
    """Codegen-level tests for DO command code generation (§8.2.3)."""

    def test_do_call_codegen(self, generate_python):
        """DO generates function call (§8.2.3).

        User Story 5 acceptance scenario (T042/T043):
        Given: D SUB
        When: generated
        Then: output contains SUB() function call
        """
        code = generate_python('TEST\n D SUB\n Q\nSUB\n W "SUB"\n Q\n')
        assert "SUB()" in code

    def test_do_call_and_return(self, execute_mumps):
        """DO calls subroutine and returns to caller.

        User Story 5 acceptance scenario (T043):
        Given: TEST D SUB W "END" Q SUB W "SUB" Q
        When: generated and executed
        Then: output is "SUBEND" (SUB writes, then returns, then END writes)
        """
        result = execute_mumps('TEST\n D SUB\n W "END"\n Q\nSUB\n W "SUB"\n Q\n')
        assert result.output == "SUBEND"
        assert result.success is True

    def test_do_nested_calls(self, execute_mumps):
        """Nested DO calls work correctly.

        User Story 5 acceptance scenario (T044):
        Given: TEST D A Q A D B Q B W "B" Q
        When: generated and executed
        Then: output is "B" (TEST→A→B, B writes)
        """
        result = execute_mumps('TEST\n D A\n Q\nA\n D B\n Q\nB\n W "B"\n Q\n')
        assert result.output == "B"
        assert result.success is True

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO with args")
    def test_do_with_args(self, generate_python):
        """DO with arguments generates parameterized call (§8.2.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO block codegen")
    def test_do_block_codegen(self, generate_python):
        """DO block generates indented block (§8.2.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO external routine")
    def test_do_external_routine(self, generate_python):
        """DO external routine generates import and call (§8.2.3)."""
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestTestStackArgumentlessDo:
    """Codegen tests for $TEST stacking with argumentless DO (Spec 005 US1).

    Argumentless DO (D SUB without arguments) saves $TEST before the call
    and restores it after QUIT. This ensures subsequent ELSE statements
    see the caller's $TEST value, not the callee's.

    Reference: §8.2.3, MUMPS 1995 ANSI Standard 7.1.2.3
    """

    def test_argumentless_do_saves_test(self, generate_python):
        """Argumentless DO generates _saved_test = _test before call (T009/T010).

        User Story 1 acceptance scenario:
        Given: D SUB
        When: generated
        Then: code contains _saved_test = _test before SUB()
        """
        code = generate_python("TEST\n D SUB\n Q\nSUB\n I 0\n Q\n")
        assert "_saved_test = _test" in code
        assert "SUB()" in code

    def test_argumentless_do_restores_test(self, generate_python):
        """Argumentless DO generates _test = _saved_test after call (T011).

        User Story 1 acceptance scenario:
        Given: D SUB
        When: generated
        Then: code contains _test = _saved_test after SUB()
        """
        code = generate_python("TEST\n D SUB\n Q\nSUB\n I 0\n Q\n")
        # Verify restore appears after call
        save_pos = code.find("_saved_test = _test")
        call_pos = code.find("SUB()")
        restore_pos = code.find("_test = _saved_test")
        assert save_pos < call_pos < restore_pos

    def test_argumentless_do_else_sees_original_test(self, execute_mumps):
        """ELSE after argumentless DO sees original $TEST (T012).

        User Story 1 acceptance scenario 1:
        Given: TEST I 1 D SUB E W "BAD" Q SUB I 0 Q
        When: generated and executed
        Then: output is empty (ELSE should NOT execute because $TEST
              was 1 before DO, restored after even though SUB sets $TEST=0)
        """
        result = execute_mumps('TEST\n I 1\n D SUB\n E  W "BAD"\n Q\nSUB\n I 0\n Q\n')
        assert result.output == ""
        assert result.success is True

    def test_argumentless_do_else_executes_on_false(self, execute_mumps):
        """ELSE after argumentless DO executes if original $TEST was 0 (T012).

        User Story 1 acceptance scenario 2:
        Given: TEST I 0 D SUB E W "GOOD" Q SUB I 0 Q
        When: generated and executed
        Then: output is "GOOD" (ELSE executes because $TEST was 0
              before DO, restored after)
        """
        result = execute_mumps('TEST\n I 0\n D SUB\n E  W "GOOD"\n Q\nSUB\n I 0\n Q\n')
        assert result.output == "GOOD"
        assert result.success is True

    def test_nested_argumentless_do_restores_correctly(self, execute_mumps):
        """Nested argumentless DO preserves outer $TEST (T013).

        User Story 1 acceptance scenario 3:
        Given: TEST I 1 D A E W "OUTER" Q A D B Q B I 0 Q
        When: generated and executed
        Then: output is empty (outer ELSE sees restored $TEST=1,
              not B's $TEST=0)
        """
        result = execute_mumps(
            'TEST\n I 1\n D A\n E  W "OUTER"\n Q\nA\n D B\n Q\nB\n I 0\n Q\n'
        )
        assert result.output == ""
        assert result.success is True

    def test_nested_argumentless_do_inner_sees_correct_test(self, execute_mumps):
        """Inner subroutine operates on its own $TEST context (T013).

        Each level of argumentless DO has its own $TEST stack frame.
        """
        # TEST sets $TEST=1, calls A which sets $TEST=0, A has ELSE that should fire
        result = execute_mumps('TEST\n I 1\n D A\n Q\nA\n I 0\n E  W "A-ELSE"\n Q\n')
        assert result.output == "A-ELSE"
        assert result.success is True


@pytest.mark.codegen
class TestTestStackDoWithArgs:
    """Codegen tests for $TEST NOT stacked with DO with arguments (Spec 005 US2).

    DO with arguments (D SUB(X) or D SUB()) does NOT save/restore $TEST.
    Changes made by the callee ARE visible to the caller.

    Reference: §8.2.3, MUMPS 1995 ANSI Standard 7.1.2.3
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO with args codegen")
    def test_do_with_args_no_test_save(self, generate_python):
        """DO with args does NOT generate _saved_test (T015).

        User Story 2 scenario:
        Given: D SUB(1)
        When: generated
        Then: code does NOT contain _saved_test pattern
        """
        pytest.fail("Stub - implement in Phase 4 (US2)")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO with args $TEST visibility")
    def test_do_with_args_callee_test_visible(self, execute_mumps):
        """Callee's $TEST changes visible to caller after DO with args (T016).

        User Story 2 acceptance scenario 1:
        Given: TEST I 1 D SUB(1) E W "ELSE" Q SUB(X) I 0 Q
        When: generated and executed
        Then: output is "ELSE" ($TEST=0 from callee IS visible)
        """
        pytest.fail("Stub - implement in Phase 4 (US2)")


@pytest.mark.codegen
class TestIsArgumentlessDoHelper:
    """Tests for _is_argumentless_do() helper function (T009)."""

    def test_is_argumentless_do_no_args(self):
        """D SUB is argumentless (no argument list)."""
        from m2py.asg.elements import MCall
        from m2py.asg.statements import MDoStatement
        from m2py.codegen.statements import _is_argumentless_do

        target = MCall(name="SUB")
        # Default arguments is empty list - which means argumentless
        stmt = MDoStatement(targets=[target])

        assert _is_argumentless_do(stmt) is True

    def test_is_argumentless_do_empty_args(self):
        """D SUB() with empty args list is still argumentless for MCall."""
        from m2py.asg.elements import MCall
        from m2py.asg.statements import MDoStatement
        from m2py.codegen.statements import _is_argumentless_do

        target = MCall(name="SUB", arguments=[])
        stmt = MDoStatement(targets=[target])

        # Empty arguments list = still argumentless
        assert _is_argumentless_do(stmt) is True

    def test_is_argumentless_do_with_args(self):
        """D SUB(X) is NOT argumentless (has arguments)."""
        from m2py.asg.elements import MCall
        from m2py.asg.expressions import MActualParameter, MVariable
        from m2py.asg.statements import MDoStatement
        from m2py.codegen.statements import _is_argumentless_do

        # Create an actual parameter
        param = MActualParameter(expression=MVariable(name="X"))
        target = MCall(name="SUB", arguments=[param])
        stmt = MDoStatement(targets=[target])

        assert _is_argumentless_do(stmt) is False

    def test_is_argumentless_do_block(self):
        """DO block (no targets) returns False."""
        from m2py.asg.statements import MDoStatement, MScope
        from m2py.codegen.statements import _is_argumentless_do

        stmt = MDoStatement(targets=[], body=MScope(statements=[]))

        assert _is_argumentless_do(stmt) is False


@pytest.mark.codegen
class TestScopeStrategyCodegen:
    """Codegen tests for variable scope strategies.

    Based on FunctionSignature.scope_strategy, different Python patterns
    are generated for handling variable visibility and side effects.

    Reference: §6.3, §8.2.3
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: pure function codegen")
    def test_pure_function_codegen(self, generate_python):
        """PURE_FUNCTION generates simple def with return.

        No side effects, returns value: def f(args) -> T
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: subroutine codegen")
    def test_subroutine_codegen(self, generate_python):
        """SUBROUTINE generates def returning None or dict.

        Side effects only, no return value.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: function with outputs codegen")
    def test_function_with_outputs_codegen(self, generate_python):
        """FUNCTION_WITH_OUTPUTS generates tuple return.

        Returns value plus modified by-ref parameters.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: requires runtime codegen")
    def test_requires_runtime_codegen(self, generate_python):
        """REQUIRES_RUNTIME generates runtime scope access.

        Indirection/XECUTE defeats static analysis.
        """
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestByRefParameterCodegen:
    """Codegen tests for by-reference parameter handling.

    When caller uses .X, the callee can modify X. Generated code uses
    a return-tuple pattern to propagate modified values back.

    Reference: §6.3, §8.2.3
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: byref call generates tuple unpack")
    def test_byref_call_generates_tuple_unpack(self, generate_python):
        """By-reference call generates tuple unpacking at call site.

        D SWAP(.A,.B) generates: a, b = swap(a, b)
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: byref callee returns modified")
    def test_byref_callee_returns_modified(self, generate_python):
        """By-reference callee returns modified values.

        Callee returns tuple of byref_outputs values.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: mixed byref and value params")
    def test_mixed_byref_and_value_params(self, generate_python):
        """Mixed by-ref and by-value parameters handled correctly.

        D SUB(A,.B,C) - only B is by-reference.
        """
        pytest.fail("Stub - implement test")
