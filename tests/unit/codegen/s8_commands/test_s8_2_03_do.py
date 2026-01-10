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

    def test_do_with_args(self, generate_python):
        """DO with arguments generates parameterized call (§8.2.3)."""
        code = generate_python("TEST\n D SUB(1,2)\n Q\nSUB(A,B)\n W A+B\n Q\n")
        assert "SUB(1, 2)" in code

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
    """Codegen tests for $TEST with label calls vs DO blocks (Spec 005).

    $TEST Stacking Rules (verified against YottaDB):
    - Label calls (D SUB, D SUB(), D SUB(X)) do NOT stack $TEST
    - Only DO blocks (D followed by dot lines) stack $TEST
    - Extrinsic functions ($$func) stack $TEST

    Note: "Argumentless DO" can be ambiguous - it can mean either a label
    call without args (D SUB) or a DO block. Only the latter stacks $TEST.

    Reference: §8.2.3, verified against YottaDB
    """

    def test_label_call_no_test_save(self, generate_python):
        """D SUB (label call) does NOT generate _saved_test (T009/T010).

        Label calls do NOT stack $TEST - callee's changes are visible.
        """
        code = generate_python("TEST\n D SUB\n Q\nSUB\n I 0\n Q\n")
        # Should NOT have save/restore for label calls
        assert "_saved_test = _test" not in code
        assert "SUB()" in code

    def test_label_call_callee_test_visible(self, execute_mumps):
        """ELSE after label call sees callee's $TEST (T012).

        Given: TEST I 1 D SUB E W "ELSE" Q SUB I 0 Q
        When: generated and executed
        Then: output is "ELSE" because callee set $TEST=0 and that's visible
        """
        result = execute_mumps('TEST\n I 1\n D SUB\n E  W "ELSE"\n Q\nSUB\n I 0\n Q\n')
        assert result.output == "ELSE"
        assert result.success is True

    def test_label_call_else_on_true(self, execute_mumps):
        """ELSE after label call does NOT execute if callee set $TEST=1.

        Given: TEST I 0 D SUB E W "ELSE" Q SUB I 1 Q
        When: generated and executed
        Then: output is empty because callee set $TEST=1
        """
        result = execute_mumps('TEST\n I 0\n D SUB\n E  W "ELSE"\n Q\nSUB\n I 1\n Q\n')
        assert result.output == ""
        assert result.success is True

    def test_nested_label_calls_no_stacking(self, execute_mumps):
        """Nested label calls do NOT create isolated $TEST context.

        Given: TEST I 1 D A E W "OUTER" Q A D B Q B I 0 Q
        When: generated and executed
        Then: output is "OUTER" because B's $TEST=0 is visible to TEST
        """
        result = execute_mumps(
            'TEST\n I 1\n D A\n E  W "OUTER"\n Q\nA\n D B\n Q\nB\n I 0\n Q\n'
        )
        assert result.output == "OUTER"
        assert result.success is True

    def test_inner_else_sees_own_test(self, execute_mumps):
        """Inner subroutine's ELSE sees its own $TEST, not caller's."""
        # TEST sets $TEST=1, calls A which sets $TEST=0, A has ELSE that should fire
        result = execute_mumps('TEST\n I 1\n D A\n Q\nA\n I 0\n E  W "A-ELSE"\n Q\n')
        assert result.output == "A-ELSE"
        assert result.success is True


@pytest.mark.codegen
class TestTestStackDoWithArgs:
    """Codegen tests for $TEST with DO with arguments (Spec 005 US2).

    DO with arguments (D SUB(X) or D SUB()) does NOT save/restore $TEST.
    Changes made by the callee ARE visible to the caller.

    This is the SAME behavior as D SUB (label call without args).
    All label calls have the same $TEST semantics.

    Reference: §8.2.3, verified against YottaDB
    """

    def test_do_with_args_no_test_save(self, generate_python):
        """DO with args does NOT generate _saved_test (T015).

        User Story 2 scenario:
        Given: D SUB(1)
        When: generated
        Then: code does NOT contain _saved_test pattern
        """
        code = generate_python("TEST\n D SUB(1)\n Q\nSUB(X)\n W X\n Q\n")
        # Should NOT have save/restore for label calls with args
        assert "_saved_test = _test" not in code
        assert "SUB(1)" in code

    def test_do_with_args_callee_test_visible(self, execute_mumps):
        """Callee's $TEST changes visible to caller after DO with args (T016).

        User Story 2 acceptance scenario 1:
        Given: TEST I 1 D SUB(1) E W "ELSE" Q SUB(X) I 0 Q
        When: generated and executed
        Then: output is "ELSE" ($TEST=0 from callee IS visible)

        Note: This test requires Phase 9 (US7) for proper formal parameter
        generation in function signatures.
        """
        # For now, test with a label that doesn't need formal params
        # Full test deferred to Phase 9
        result = execute_mumps('TEST\n I 1\n D SUB\n E  W "ELSE"\n Q\nSUB\n I 0\n Q\n')
        assert result.output == "ELSE"
        assert result.success is True

    @pytest.mark.xfail(reason="Depends on Phase 9 (US7) for formal parameter support")
    def test_do_with_args_callee_test_visible_full(self, execute_mumps):
        """Full test for DO with args $TEST visibility (requires Phase 9)."""
        result = execute_mumps(
            'TEST\n I 1\n D SUB(1)\n E  W "ELSE"\n Q\nSUB(X)\n I 0\n Q\n'
        )
        assert result.output == "ELSE"
        assert result.success is True

    def test_do_with_empty_args_no_test_save(self, generate_python):
        """D SUB() does NOT generate _saved_test (T017).

        Empty args still a label call, not a DO block.
        """
        code = generate_python("TEST\n D SUB()\n Q\nSUB()\n I 0\n Q\n")
        # Should NOT have save/restore for label calls with empty args
        assert "_saved_test = _test" not in code
        assert "SUB()" in code

    def test_do_with_empty_args_callee_test_visible(self, execute_mumps):
        """D SUB() - callee's $TEST visible to caller.

        Same as D SUB - NOT a DO block.
        """
        result = execute_mumps(
            'TEST\n I 1\n D SUB()\n E  W "ELSE"\n Q\nSUB()\n I 0\n Q\n'
        )
        assert result.output == "ELSE"
        assert result.success is True


@pytest.mark.codegen
class TestIsDoBlockHelper:
    """Tests for _is_do_block() helper function.

    This helper detects DO blocks (D followed by dot-indented lines),
    which is the ONLY form of DO that stacks $TEST.
    """

    def test_is_do_block_with_body(self):
        """DO block with statements returns True."""
        from m2py.asg.statements import MDoStatement, MScope, MSetStatement
        from m2py.codegen.statements import _is_do_block

        # DO block has no targets but has body
        body_stmt = MSetStatement(assignments=[])
        stmt = MDoStatement(targets=[], body=MScope(statements=[body_stmt]))

        assert _is_do_block(stmt) is True

    def test_is_do_block_empty_body(self):
        """DO block without statements returns False."""
        from m2py.asg.statements import MDoStatement, MScope
        from m2py.codegen.statements import _is_do_block

        stmt = MDoStatement(targets=[], body=MScope(statements=[]))

        assert _is_do_block(stmt) is False

    def test_is_do_block_label_call(self):
        """D SUB (label call) returns False - NOT a block."""
        from m2py.asg.elements import MCall
        from m2py.asg.statements import MDoStatement
        from m2py.codegen.statements import _is_do_block

        target = MCall(name="SUB")
        stmt = MDoStatement(targets=[target])

        assert _is_do_block(stmt) is False

    def test_is_do_block_label_call_with_args(self):
        """D SUB(X) returns False - NOT a block."""
        from m2py.asg.elements import MCall
        from m2py.asg.expressions import MActualParameter, MVariable
        from m2py.asg.statements import MDoStatement
        from m2py.codegen.statements import _is_do_block

        param = MActualParameter(expression=MVariable(name="X"))
        target = MCall(name="SUB", arguments=[param])
        stmt = MDoStatement(targets=[target])

        assert _is_do_block(stmt) is False


@pytest.mark.codegen
class TestGenerateCallArgumentsHelper:
    """Tests for _generate_call_arguments() helper function.

    This helper generates Python argument strings from MUMPS call arguments.
    """

    def test_empty_arguments(self):
        """Empty arguments returns empty string."""
        from m2py.codegen.statements import _generate_call_arguments

        result = _generate_call_arguments([], None)
        assert result == ""

    def test_single_literal_argument(self):
        """Single literal argument generates value."""
        from unittest.mock import MagicMock

        from m2py.asg.enums import LiteralType, PassingMode
        from m2py.asg.expressions import MActualParameter, MLiteral
        from m2py.codegen.statements import _generate_call_arguments

        ctx = MagicMock()
        arg = MActualParameter(
            passing_mode=PassingMode.BY_VALUE,
            expression=MLiteral(value="1", literal_type=LiteralType.INTEGER),
        )

        result = _generate_call_arguments([arg], ctx)
        assert result == "1"

    def test_multiple_arguments(self):
        """Multiple arguments generates comma-separated list."""
        from unittest.mock import MagicMock

        from m2py.asg.enums import LiteralType, PassingMode
        from m2py.asg.expressions import MActualParameter, MLiteral
        from m2py.codegen.statements import _generate_call_arguments

        ctx = MagicMock()
        arg1 = MActualParameter(
            passing_mode=PassingMode.BY_VALUE,
            expression=MLiteral(value="1", literal_type=LiteralType.INTEGER),
        )
        arg2 = MActualParameter(
            passing_mode=PassingMode.BY_VALUE,
            expression=MLiteral(value="2", literal_type=LiteralType.INTEGER),
        )

        result = _generate_call_arguments([arg1, arg2], ctx)
        assert result == "1, 2"

    def test_omitted_argument(self):
        """Omitted argument generates None."""
        from unittest.mock import MagicMock

        from m2py.asg.enums import PassingMode
        from m2py.asg.expressions import MActualParameter
        from m2py.codegen.statements import _generate_call_arguments

        ctx = MagicMock()
        arg = MActualParameter(passing_mode=PassingMode.OMITTED)

        result = _generate_call_arguments([arg], ctx)
        assert result == "None"

    def test_byref_with_variable_name(self):
        """By-reference with variable_name uses translated name."""
        from unittest.mock import MagicMock

        from m2py.asg.enums import PassingMode
        from m2py.asg.expressions import MActualParameter
        from m2py.codegen.statements import _generate_call_arguments

        ctx = MagicMock()
        arg = MActualParameter(passing_mode=PassingMode.BY_REFERENCE, variable_name="X")

        result = _generate_call_arguments([arg], ctx)
        assert result == "X"  # translate_name preserves case

    def test_byref_with_expression(self):
        """By-reference with expression generates expression."""
        from unittest.mock import MagicMock

        from m2py.asg.enums import PassingMode
        from m2py.asg.expressions import MActualParameter, MVariable
        from m2py.codegen.statements import _generate_call_arguments

        ctx = MagicMock()
        arg = MActualParameter(
            passing_mode=PassingMode.BY_REFERENCE, expression=MVariable(name="X")
        )

        result = _generate_call_arguments([arg], ctx)
        assert result == "X"  # translate_name preserves case


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
