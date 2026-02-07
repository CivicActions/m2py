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
        Then: output contains _globals['SUB'](_rt, _scope=_scope) function call
        Phase 13 (T079): Internal DO calls now pass _rt as first argument.
        T084: Internal DO calls also pass _scope for cross-routine visibility.
        Phase 21: Use globals() lookup to prevent parameter shadowing.
        """
        code = generate_python('TEST\n D SUB\n Q\nSUB\n W "SUB"\n Q\n')
        assert "_globals['SUB'](_rt, _scope=_scope)" in code

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
        """DO with arguments generates parameterized call (§8.2.3).

        Phase 13 (T079): Internal DO calls now pass _rt as first argument.
        T084: Internal DO calls also pass _scope for cross-routine visibility.
        Phase 21: Use globals() lookup to prevent parameter shadowing.
        """
        code = generate_python("TEST\n D SUB(1,2)\n Q\nSUB(A,B)\n W A+B\n Q\n")
        assert "_globals['SUB'](_rt, 1, 2, _scope=_scope)" in code

    def test_do_block_codegen(self, generate_python):
        """DO block generates indented block with while True wrapper (§8.2.3).

        DO blocks are executed inline, with statements wrapped in
        while True: break pattern to allow early QUIT.
        """
        code = generate_python("TEST\n D\n . W 1\n . W 2\n Q\n")
        # DO block should generate while True wrapper with break
        assert "while True:" in code
        assert "break" in code
        # Body statements should write 1 and 2
        assert "_rt.write" in code

    def test_do_block_executes(self, execute_mumps):
        """DO block executes all dot-indented lines (§8.2.3)."""
        result = execute_mumps("TEST\n D\n . W 1\n . W 2\n Q\n")
        assert result.output == "12"
        assert result.success is True

    def test_nested_do_in_if_edge(self, execute_mumps):
        """Nested DO in IF executes dot-block when condition is true (§8.2.3).

        T059: IF-DO with dot-indented block
        Given: I 1 D (followed by dot-indented lines)
        When: executed
        Then: the dot-block executes because condition is true

        Reference: Finding 59 from research.md
        An IF followed by argumentless DO collects subsequent dot-lines as the DO block,
        and the block executes only if the IF condition is true.
        """
        result = execute_mumps('TEST\n I 1 D\n . W "dot-line",!\n W "after",!\n Q\n')
        assert result.output == "dot-line\nafter\n"
        assert result.success is True

    def test_nested_do_in_if_false_edge(self, execute_mumps):
        """Nested DO in IF skips dot-block when condition is false (§8.2.3).

        T059 complement: When IF condition is false, the DO block is skipped.
        """
        result = execute_mumps('TEST\n I 0 D\n . W "dot-line",!\n W "after",!\n Q\n')
        assert result.output == "after\n"
        assert result.success is True

    def test_do_external_routine(self, generate_python):
        """DO external routine generates import and call (§8.2.3).

        D LABEL^ROUTINE generates:
        1. Import statement for the external routine module
        2. Label existence check with helpful error
        3. Call via run_with_goto_support for external GOTO handling (T075e)
        """
        code = generate_python("TEST D LABEL^EXTRTN Q")

        # Should import the external routine module
        assert "import EXTRTN" in code

        # Should check if label exists with helpful error
        assert "hasattr(EXTRTN, 'LABEL')" in code
        assert "LabelNotFoundError" in code

        # Should call via run_with_goto_support for external GOTO handling
        assert "run_with_goto_support(EXTRTN.LABEL, _rt, _scope)" in code


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
        Phase 13 (T079): Internal DO calls now pass _rt as first argument.
        T084: Internal DO calls also pass _scope for cross-routine visibility.
        Phase 21: Use globals() lookup to prevent parameter shadowing.
        """
        code = generate_python("TEST\n D SUB\n Q\nSUB\n I 0\n Q\n")
        # Should NOT have save/restore for label calls
        assert "_saved_test = _test" not in code
        assert "_globals['SUB'](_rt, _scope=_scope)" in code

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

    def test_nested_do_blocks_test_isolation(self, execute_mumps):
        """Nested DO blocks maintain independent $TEST stacks (T083).

        Each DO block saves and restores $TEST independently.
        Inner block changes to $TEST don't affect outer block's $TEST.
        """
        # IF 1 sets $TEST=1
        # DO block starts (saves $TEST=1)
        # Inner IF 0 sets $TEST=0
        # DO block ends (restores $TEST=1)
        # Write $T should output 1
        source = """TEST I 1 D  W $T Q
 . I 0"""
        result = execute_mumps(source)
        assert result.output == "1"
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

    def test_do_with_args_callee_test_visible_full(self, execute_mumps):
        """Full test for DO with args $TEST visibility (Phase 9 complete)."""
        result = execute_mumps(
            'TEST\n I 1\n D SUB(1)\n E  W "ELSE"\n Q\nSUB(X)\n I 0\n Q\n'
        )
        assert result.output == "ELSE"
        assert result.success is True

    def test_do_with_empty_args_no_test_save(self, generate_python):
        """D SUB() does NOT generate _saved_test (T017).

        Empty args still a label call, not a DO block.
        Phase 13 (T079): Internal DO calls now pass _rt as first argument.
        T084: Internal DO calls also pass _scope for cross-routine visibility.
        Phase 21: Use globals() lookup to prevent parameter shadowing.
        """
        code = generate_python("TEST\n D SUB()\n Q\nSUB()\n I 0\n Q\n")
        # Should NOT have save/restore for label calls with empty args
        assert "_saved_test = _test" not in code
        # With empty args, it generates _globals['SUB'](_rt, _scope=_scope)
        assert "_globals['SUB'](_rt, _scope=_scope)" in code

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
class TestIsInlineBlockField:
    """Tests for MDoStatement.is_inline_block field.

    This field is set by the parser when dot-indented lines are collected
    into a DO block body. It's the ONLY form of DO that stacks $TEST.
    """

    def test_is_inline_block_set_by_parser(self):
        """Parser sets is_inline_block when DO block has body statements."""
        from m2py import MUMPSParser

        source = """TEST D
 . S X=1
 Q
"""
        parser = MUMPSParser()
        routine = parser.parse(source)

        # Find the DO statement
        from m2py.asg.statements import MDoStatement

        do_stmt = None
        for label in routine.labels:
            for stmt in label.body.walk_statements():
                if isinstance(stmt, MDoStatement):
                    do_stmt = stmt
                    break
            if do_stmt:
                break

        assert do_stmt is not None
        assert do_stmt.is_inline_block is True

    def test_is_inline_block_false_for_label_call(self):
        """D SUB (label call) has is_inline_block=False."""
        from m2py import MUMPSParser

        source = """TEST D SUB
 Q
SUB W "Hello"
 Q
"""
        parser = MUMPSParser()
        routine = parser.parse(source)

        # Find the DO statement in TEST label
        from m2py.asg.statements import MDoStatement

        do_stmt = None
        for label in routine.labels:
            if label.name == "TEST":
                for stmt in label.body.walk_statements():
                    if isinstance(stmt, MDoStatement):
                        do_stmt = stmt
                        break
                break

        assert do_stmt is not None
        assert do_stmt.is_inline_block is False

    def test_is_inline_block_default_value(self):
        """New MDoStatement has is_inline_block=False by default."""
        from m2py.asg.statements import MDoStatement

        stmt = MDoStatement(targets=[])
        assert stmt.is_inline_block is False


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

    def test_pure_function_codegen(self):
        """PURE_FUNCTION is detected for functions with no side effects.

        A function that only returns a value and doesn't:
        - Modify caller variables
        - Access globals
        - Have side effects
        Should be classified as PURE_FUNCTION.
        """
        from m2py import MUMPSParser
        from m2py.analysis.variables import compute_all_signatures
        from m2py.asg.enums import ScopeStrategy

        parser = MUMPSParser()
        # Pure function - just returns a value
        routine = parser.parse("TEST Q $$ADD(1,2)\nADD(X,Y) Q X+Y")
        parser.resolve_references(routine)
        parser.analyze_variables(routine)

        sigs = compute_all_signatures(routine)
        # ADD should be classified as PURE_FUNCTION
        assert sigs["ADD"].scope_strategy == ScopeStrategy.PURE_FUNCTION

    def test_subroutine_codegen(self):
        """SUBROUTINE is detected for procedures with side effects.

        A label that:
        - Has no return value (QUIT without expression)
        - May have side effects (writes, globals, etc.)
        Should be classified as SUBROUTINE.
        """
        from m2py import MUMPSParser
        from m2py.analysis.variables import compute_all_signatures
        from m2py.asg.enums import ScopeStrategy

        parser = MUMPSParser()
        # Subroutine - writes output, no return value
        routine = parser.parse('TEST D SUB Q\nSUB W "Hello" Q')
        parser.resolve_references(routine)
        parser.analyze_variables(routine)

        sigs = compute_all_signatures(routine)
        # Both TEST and SUB should be classified as SUBROUTINE
        assert sigs["SUB"].scope_strategy == ScopeStrategy.SUBROUTINE
        assert sigs["TEST"].scope_strategy == ScopeStrategy.SUBROUTINE

    def test_function_with_outputs_codegen(self):
        """FUNCTION_WITH_OUTPUTS is detected for functions returning value + by-ref.

        A function that:
        - Returns a value (QUIT with expression)
        - Also modifies by-ref parameters
        Should be classified as FUNCTION_WITH_OUTPUTS.
        """
        from m2py import MUMPSParser
        from m2py.analysis.variables import compute_all_signatures
        from m2py.asg.enums import ScopeStrategy

        parser = MUMPSParser()
        # Function with outputs - returns value AND modifies by-ref param X
        routine = parser.parse("TEST S A=1 S R=$$INC(.A) Q\nINC(X) S X=X+1 Q X")
        parser.resolve_references(routine)
        parser.analyze_variables(routine)

        sigs = compute_all_signatures(routine)
        # INC should be classified as FUNCTION_WITH_OUTPUTS
        assert sigs["INC"].scope_strategy == ScopeStrategy.FUNCTION_WITH_OUTPUTS
        # It should also have X in byref_outputs
        assert "X" in sigs["INC"].byref_outputs

    def test_requires_runtime_codegen(self):
        """REQUIRES_RUNTIME is detected when indirection defeats static analysis.

        A label that uses:
        - Indirection (D @var, S @var=...)
        - XECUTE
        Should be classified as REQUIRES_RUNTIME.
        """
        from m2py import MUMPSParser
        from m2py.analysis.variables import compute_all_signatures
        from m2py.asg.enums import ScopeStrategy

        parser = MUMPSParser()
        # Requires runtime - uses indirection
        routine = parser.parse('TEST S X="SUB" D @X Q\nSUB W "OK" Q')
        parser.resolve_references(routine)
        parser.analyze_variables(routine)

        sigs = compute_all_signatures(routine)
        # TEST should be classified as REQUIRES_RUNTIME
        assert sigs["TEST"].scope_strategy == ScopeStrategy.REQUIRES_RUNTIME
        # SUB should be SUBROUTINE (no indirection)
        assert sigs["SUB"].scope_strategy == ScopeStrategy.SUBROUTINE


@pytest.mark.codegen
class TestByRefParameterCodegen:
    """Codegen tests for by-reference parameter handling (Spec 005 Phase 10).

    When caller uses .X, the callee can modify X. Generated code uses
    a return-tuple pattern to propagate modified values back.

    Reference: §6.3, §8.2.3
    """

    def test_incr_single_byref_param(self, generate_python):
        """INCR pattern with single by-ref param (T064).

        D INCR(.X) passes MArray directly for true call-by-reference aliasing.
        Callee detects isinstance(N, MArray) and uses it as alias.
        """
        code = generate_python("TEST S X=5 D INCR(.X) W X Q\nINCR(N) S N=N+1 Q\n")

        # Phase 13 (T076): Callee signature includes _rt as first parameter
        # Phase 19 (Spec 017): Formal params have =None default
        assert "def INCR(_rt, N=None, _scope=None, _start_offset=0):" in code

        # Phase 21: Callee uses isinstance check for by-ref MArray aliasing
        assert "if isinstance(N, MArray):" in code
        assert "_scope['N'] = N" in code

        # Phase 21: Call site passes MArray directly for by-ref aliasing
        assert (
            "_globals['INCR'](_rt, _scope.setdefault('X', MArray()), _scope=_scope)"
            in code
        )

    def test_incr_single_byref_runtime(self, execute_mumps):
        """INCR pattern executes correctly with by-ref (T064).

        Given: X=5, D INCR(.X), W X
        When: executed
        Then: output is "6" (X was incremented)
        """
        result = execute_mumps("TEST S X=5 D INCR(.X) W X Q\nINCR(N) S N=N+1 Q\n")
        assert result.output == "6"
        assert result.success is True

    def test_swap_two_byref_params(self, generate_python):
        """SWAP pattern with two by-ref params (T063).

        D SWAP(.A,.B) passes MArray objects directly for true aliasing.
        """
        code = generate_python(
            "TEST S A=1,B=2 D SWAP(.A,.B) W A,B Q\nSWAP(X,Y) S T=X,X=Y,Y=T Q\n"
        )

        # Phase 13 (T076): Callee signature includes _rt as first parameter
        # Phase 19 (Spec 017): Formal params have =None default
        assert "def SWAP(_rt, X=None, Y=None, _scope=None, _start_offset=0):" in code

        # Phase 21: Callee uses isinstance check for by-ref MArray aliasing
        assert "if isinstance(X, MArray):" in code
        assert "_scope['X'] = X" in code
        assert "if isinstance(Y, MArray):" in code
        assert "_scope['Y'] = Y" in code

        # Phase 21: Call site passes MArrays directly for by-ref aliasing
        assert (
            "_globals['SWAP'](_rt, _scope.setdefault('A', MArray()), _scope.setdefault('B', MArray()), _scope=_scope)"
            in code
        )

    def test_swap_two_byref_runtime(self, execute_mumps):
        """SWAP pattern executes correctly with two by-refs (T063).

        Given: A=1, B=2, D SWAP(.A,.B), W A,B
        When: executed
        Then: output is "21" (values swapped)
        """
        result = execute_mumps(
            "TEST S A=1,B=2 D SWAP(.A,.B) W A,B Q\nSWAP(X,Y) S T=X,X=Y,Y=T Q\n"
        )
        assert result.output == "21"
        assert result.success is True

    def test_multiple_byref_calls_accumulate(self, generate_python):
        """Multiple by-ref calls accumulate changes (T065).

        D INCR(.X),INCR(.X),INCR(.X) passes MArray three times for aliasing.
        """
        code = generate_python(
            "TEST S X=1 D INCR(.X),INCR(.X),INCR(.X) W X Q\nINCR(N) S N=N+1 Q\n"
        )

        # Phase 21: Three separate calls passing MArray for by-ref aliasing
        assert (
            code.count(
                "_globals['INCR'](_rt, _scope.setdefault('X', MArray()), _scope=_scope)"
            )
            == 3
        )

    def test_multiple_byref_calls_runtime(self, execute_mumps):
        """Multiple by-ref calls accumulate correctly (T065).

        Given: X=1, D INCR(.X),INCR(.X),INCR(.X), W X
        When: executed
        Then: output is "4" (incremented 3 times)
        """
        result = execute_mumps(
            "TEST S X=1 D INCR(.X),INCR(.X),INCR(.X) W X Q\nINCR(N) S N=N+1 Q\n"
        )
        assert result.output == "4"
        assert result.success is True

    def test_byvalue_call_no_destructure(self, generate_python):
        """By-value call does not destructure even if callee has byref_outputs.

        D INCR(X) (no dot) passes by value - caller's X unchanged.
        """
        code = generate_python("TEST S X=5 D INCR(X) W X Q\nINCR(N) S N=N+1 Q\n")

        # By-value call should not destructure
        # Phase 13 (T079) + T084: Call passes _scope but no assignment to _scope['X']
        lines = [line.strip() for line in code.split("\n")]
        # Find the line that calls INCR in TEST function
        # It should be just "_globals['INCR'](_rt, _scope.get('X', ''), _scope=_scope)" not "_scope['X'] = _globals['INCR'](...)"
        incr_lines = [
            line
            for line in lines
            if "_globals['INCR'](_rt," in line and "_scope=_scope)" in line
        ]
        # Should have INCR call without _scope['X'] = assignment
        assert any(not line.startswith("_scope['X']") for line in incr_lines)

    def test_byvalue_call_runtime(self, execute_mumps):
        """By-value call does not modify caller's variable.

        Given: X=5, D INCR(X) (no dot), W X
        When: executed
        Then: output is "5" (X unchanged, N was a copy)
        """
        result = execute_mumps("TEST S X=5 D INCR(X) W X Q\nINCR(N) S N=N+1 Q\n")
        assert result.output == "5"
        assert result.success is True


# =============================================================================
# Phase 7: Indirect DO Tests (Spec 012, T042-T048)
# =============================================================================


@pytest.mark.codegen
class TestIndirectDoCodegen:
    """Codegen tests for indirect DO (D @CMD).

    Spec 012 Phase 7 (T042-T045): Support D @CMD for dynamic subroutine dispatch.

    Indirect DO resolves the call target at runtime, allowing dynamic
    dispatch based on variable contents.

    Reference: §8.2.3, MUMPS 1995 ANSI Standard
    """

    def test_indirect_do_generates_runtime_dispatch(self, generate_python):
        """D @CMD generates runtime resolve_do_targets dispatch (T042).

        The generated code should:
        1. Evaluate the indirection expression
        2. Call _rt.resolve_do_targets() to resolve and parse targets
        3. Loop over targets and dispatch to resolved functions
        """
        code = generate_python('TEST S CMD="SUB" D @CMD Q\nSUB W "Hello" Q\n')

        # Should call resolve_do_targets (handles multi-target and nested indirection)
        assert "resolve_do_targets" in code
        # Should have dispatch logic
        assert "_func" in code or "_labels" in code

    def test_indirect_do_basic_execution(self, execute_mumps):
        """S CMD="SUB" D @CMD calls SUB (T048).

        Spec 012 Phase 7 acceptance scenario:
        Given: S CMD="SUB" D @CMD
        When: executed
        Then: SUB subroutine is called and writes "Hello"
        """
        result = execute_mumps('TEST S CMD="SUB" D @CMD Q\nSUB W "Hello" Q\n')
        assert result.output == "Hello"
        assert result.success is True

    def test_indirect_do_returns_to_caller(self, execute_mumps):
        """D @CMD returns to caller after subroutine completes (T048).

        Given: S CMD="SUB" D @CMD W "After"
        When: executed
        Then: output is "HelloAfter" (SUB writes, returns, caller continues)
        """
        result = execute_mumps('TEST S CMD="SUB" D @CMD W "After" Q\nSUB W "Hello" Q\n')
        assert result.output == "HelloAfter"
        assert result.success is True

    def test_indirect_routine_call_edge(self, execute_mumps):
        """Indirect DO with dynamically computed label exercises full dispatch (§8.2.3).

        T062: Indirect DO with dynamically computed label
        Given: F I=1:1:3 S X="L"_I D @X
        When: executed
        Then: output is "1\\n2\\n3\\n" - labels L1, L2, L3 are called in sequence

        Reference: Finding from research.md
        This exercises the full indirect DO dispatch path where the label
        is computed at runtime using string concatenation. Each iteration
        computes a different label name and dispatches to it.
        """
        result = execute_mumps(
            'TEST\n N I F I=1:1:3 S X="L"_I D @X\n Q\n'
            "L1 W 1,! Q\n"
            "L2 W 2,! Q\n"
            "L3 W 3,! Q\n"
        )
        assert result.output == "1\n2\n3\n"
        assert result.success is True


@pytest.mark.codegen
class TestIndirectDoWithOffset:
    """Tests for indirect DO with offset (D @CMD+N).

    Spec 012 Phase 7 (T045): Handle indirect DO with explicit offset.
    D @CMD+5 resolves CMD to a label, then enters at offset +5.

    Reference: §8.2.3
    """

    def test_indirect_do_with_offset_codegen(self, generate_python):
        """D @CMD+1 generates offset handling code (T045).

        The generated code should handle offset calculation:
        1. Resolve CMD to get label name
        2. Look up label's start line in _label_lines
        3. Add offset to find target line
        4. Look up _line_map to get entry point
        """
        code = generate_python(
            'TEST S CMD="SUB" D @CMD+1 Q\nSUB W "Line0"\n W "Line1" Q\n'
        )

        # Should reference _label_lines for offset calculation
        assert "_label_line" in code or "offset" in code.lower()
        # Should have resolve_do_targets (which handles multi-target and nested indirection)
        assert "resolve_do_targets" in code

    def test_indirect_do_with_offset_execution(self, execute_mumps):
        """D @CMD+1 enters subroutine at offset +1 (T045).

        Given: S CMD="SUB" D @CMD+1
        When: executed
        Then: skips first line of SUB, outputs "Line1" only
        """
        result = execute_mumps(
            'TEST S CMD="SUB" D @CMD+1 Q\nSUB W "Line0"\n W "Line1" Q\n'
        )
        assert result.output == "Line1"
        assert result.success is True

    def test_indirect_do_offset_zero(self, execute_mumps):
        """D @CMD+0 is equivalent to D @CMD (starts at label).

        Given: S CMD="SUB" D @CMD+0
        When: executed
        Then: outputs "Line0Line1" (full subroutine)
        """
        result = execute_mumps(
            'TEST S CMD="SUB" D @CMD+0 Q\nSUB W "Line0"\n W "Line1" Q\n'
        )
        assert result.output == "Line0Line1"
        assert result.success is True


@pytest.mark.codegen
class TestPartialIndirection:
    """Tests for partial indirection in DO (D LABEL^@RTN, D @LBL^ROUTINE).

    Spec 012 Phase 7 (T044): Handle partial indirection where only
    part of the call target is indirect.

    Reference: §8.2.3
    """

    def test_label_indirect_routine_static_codegen(self, generate_python):
        """D @LBL generates indirection for label only (T044).

        When only the label is indirect, the routine is this module.
        """
        code = generate_python('TEST S LBL="SUB" D @LBL Q\nSUB W "OK" Q\n')

        # Should use resolve_do_targets for runtime resolution
        assert "resolve_do_targets" in code
        # Generated code handles local dispatch
        assert "_labels" in code or "_func" in code

    def test_label_indirect_execution(self, execute_mumps):
        """D @LBL calls label stored in variable (T044).

        Given: S LBL="SUB" D @LBL
        When: executed
        Then: SUB is called
        """
        result = execute_mumps('TEST S LBL="SUB" D @LBL Q\nSUB W "Called" Q\n')
        assert result.output == "Called"
        assert result.success is True

    def test_routine_indirect_codegen(self, generate_python):
        """D LABEL^@RTN generates runtime import with importlib (T044).

        When the routine is indirect, we need:
        1. Evaluate RTN variable to get routine name
        2. Use importlib.import_module() for dynamic import
        3. Call the resolved label
        """
        code = generate_python('TEST S RTN="MYRTN" D LABEL^@RTN Q')

        # Should use importlib for dynamic import
        assert "importlib.import_module" in code

        # Should evaluate the RTN variable
        assert "_scope.get('RTN'" in code

        # Should handle the call target via runtime resolve_do_targets
        assert "resolve_do_targets" in code


@pytest.mark.codegen
class TestDoWithOffsetTrampoline:
    """Tests for DO label+offset following trampoline transitions (T075i).

    When DO label+offset lands at the end of a label block, the internal
    function returns a label transition to continue execution. The generated
    code must follow this trampoline loop rather than ignoring the return.

    Fix: Changed DO offset codegen to capture return value and follow
    trampoline loop: `target, state = func(...); while target: ...`
    """

    def test_do_offset_follows_label_transition(self, execute_mumps):
        """D 12+3 where offset lands after label 12 block, before label IF.

        Label 12 has 3 offset lines (0,1,2), then label IF starts.
        D 12+3 should execute the IF label's first line.
        """
        result = execute_mumps("""TEST
 S V=""
 D LABEL+3
 W V
 Q
LABEL S V=V_"LABEL " Q
 S V=V_"LINE1 " Q
 S V=V_"LINE2 " Q
NEXT S V=V_"NEXT " Q
 S V=V_"LINE4 " Q
""")
        assert result.success is True
        assert result.output == "NEXT "

    def test_do_offset_with_unary_expression(self, execute_mumps):
        """D label+++-expr computes offset correctly and follows transition.

        This is the actual test case from V1DO3 I-246.
        D 12+++-"-.037E+2" = D 12+3 (unary chain evaluates to 3.7, int to 3)
        """
        result = execute_mumps("""TEST
 S V=""
 D LABEL+++-"-.037E+2"
 W V
 Q
LABEL S V=V_"LABEL " Q
 S V=V_"LINE1 " Q
 S V=V_"LINE2 " Q
 S V=V_"LINE3 " Q
 S V=V_"LINE4 " Q
""")
        assert result.success is True
        assert result.output == "LINE3 "

    def test_do_offset_direct_execution(self, execute_mumps):
        """D LABEL+1 executes offset 1 directly without transition."""
        result = execute_mumps("""TEST
 S V=""
 D LABEL+1
 W V
 Q
LABEL S V=V_"LABEL " Q
 S V=V_"LINE1 " Q
 S V=V_"LINE2 " Q
""")
        assert result.success is True
        assert result.output == "LINE1 "


@pytest.mark.codegen
class TestCrossRoutineScopeSync:
    """Tests for T075k: Cross-routine scope sync with MArray wrapping.

    When a routine using dynamic_locals calls an external routine that uses
    static state variables, the callee stores raw values back to _scope.
    The caller must wrap these raw values in MArray when syncing back to
    state._locals, since the caller's expression codegen expects MArray.value.

    Fix: Changed scope sync from simple update() to a loop that wraps non-MArray
    values in MArray before storing in state._locals.
    """

    def test_cross_routine_variable_visibility(self, execute_mumps):
        """Variable set in callee is visible to dynamic_locals caller.

        This simulates the V1PRGD/V1PRGD3 scenario where:
        - V1PRGD uses dynamic_locals (KILL clears all)
        - V1PRGD3 uses static state (sets VCOMP)
        - After D ^V1PRGD3, V1PRGD should see VCOMP value

        We test with argumentless KILL to force dynamic_locals usage.
        """
        result = execute_mumps("""TEST
 K
 S X=1
 D SUB
 W VCOMP
 Q
SUB S VCOMP=1234
 Q
""")
        assert result.success is True
        assert result.output == "1234"

    def test_variable_set_after_kill_visible(self, execute_mumps):
        """Variables set after KILL are properly MArray wrapped."""
        result = execute_mumps("""TEST
 K
 S A=1,B=2,C=3
 D SUB
 W A,"-",B,"-",C
 Q
SUB S A=10,C=30
 Q
""")
        assert result.success is True
        assert result.output == "10-2-30"


@pytest.mark.codegen
class TestDoLabelOffsetExternal:
    """T100: Tests for D label+offset^ROUTINE strategy detection.

    When calling D LABEL+N^ROUTINE, codegen must detect at runtime whether the
    target module uses TRAMPOLINE (internal _-prefixed functions) or SIMPLE_FUNCTIONS
    (public functions) and call appropriately.
    """

    def test_d_label_plus_n_external_strategy_detection(self, generate_python):
        """D LABEL+N^ROUTINE generates runtime strategy detection code.

        T100: The generated code should check if internal _-prefixed function exists
        and use TRAMPOLINE path with call_external_with_offset helper if so,
        SIMPLE_FUNCTIONS path otherwise.
        """
        code = generate_python("TEST\n D SUB+2^EXTRTN\n Q")

        # Should import the module
        assert "import EXTRTN" in code

        # Should have runtime strategy detection
        assert "_internal_name = '_' + _label_name" in code
        assert "hasattr(EXTRTN, _internal_name)" in code

        # Should have TRAMPOLINE branch using call_external_with_offset helper
        assert "call_external_with_offset" in code

        # Should have SIMPLE_FUNCTIONS fallback branch
        assert "getattr(EXTRTN, _label_name)" in code

        # SIMPLE_FUNCTIONS branch uses run_with_goto_support
        assert "run_with_goto_support" in code

        # verify valid Python syntax
        compile(code, "<test>", "exec")

    def test_d_offset_only_external_strategy_detection(self, generate_python):
        """D +N^ROUTINE generates runtime strategy detection code.

        T100: Offset-only calls also need strategy detection.
        """
        code = generate_python("TEST\n D +5^EXTRTN\n Q")

        # Should have runtime strategy detection for line-based dispatch
        assert "import EXTRTN" in code
        assert "_line_map" in code

        # verify valid Python syntax
        compile(code, "<test>", "exec")


@pytest.mark.codegen
class TestDoMiniTrampolineGotoExternal:
    """Tests for GotoExternal handling in DO mini-trampoline.

    When DO with offset (D LABEL+N) is executed, the code runs a mini-trampoline
    that follows label transitions. If an external GOTO is raised from within
    a subroutine called via DO, the mini-trampoline must catch it, execute
    the external routine, sync state back, and continue after the DO.
    """

    def test_do_offset_catches_goto_external(self, generate_python):
        """DO with offset generates try/except for GotoExternal.

        The mini-trampoline loop should be wrapped in try/except to catch
        GotoExternal raised from subroutines.
        """
        code = generate_python('TEST\n D SUB+1\n W "after"\n Q\nSUB\n W 1\n W 2 Q\n')

        # Should have try/except for GotoExternal
        assert "except GotoExternal as _goto:" in code
        # Should import resolve_goto_target and run_with_goto_support
        assert "resolve_goto_target" in code
        assert "run_with_goto_support" in code

    def test_do_offset_syncs_scope_after_external_call(self, generate_python):
        """After external GOTO, scope changes are synced back to state.

        When GotoExternal is caught and the external routine runs, any
        changes it made to _scope must be synced back to the caller's state.
        """
        code = generate_python("TEST\n D SUB+1\n W X\n Q\nSUB\n W 1\n W 2 Q\n")

        # After catching GotoExternal and running external routine,
        # should sync _scope back to state
        # For dynamic state: uses state._locals
        # For static state: uses setattr
        assert (
            "state._locals" in code
            or "setattr(state" in code
            or "_scope.items()" in code
        )

    def test_do_mini_trampoline_handles_int_target(self, generate_python):
        """DO mini-trampoline handles integer targets from G LABEL+N.

        T087: When an internal function returns an integer (line number)
        instead of a string (label name), the mini-trampoline should use
        _line_map to resolve it.
        """
        code = generate_python(
            "TEST\n D SUB+1\n Q\nSUB\n W 1\n G TEST+2 Q\nOTHER\n W 2 Q\n"
        )

        # Should check if target is int
        assert "isinstance(_do_target, int)" in code
        # Should use _line_map for dispatch
        assert "_line_map[_do_target]" in code

    def test_goto_external_sets_target_to_none(self, generate_python):
        """After handling GotoExternal, _do_target is set to None.

        When GotoExternal is caught and processed, the mini-trampoline
        should exit by setting _do_target = None.
        """
        code = generate_python("TEST\n D SUB+1\n Q\nSUB\n W 1\n W 2 Q\n")

        # After handling GotoExternal, target should be None to exit loop
        assert "_do_target = None" in code


@pytest.mark.codegen
class TestStateSyncEdgeCases:
    """Tests for state synchronization edge cases.

    When syncing _scope back to state after external calls, the code must
    handle both dynamic state (with _locals dict) and static state (with
    dataclass fields).
    """

    def test_state_sync_checks_for_locals_attribute(self, generate_python):
        """State sync checks for _locals attribute to determine state type.

        Dynamic state has _locals dict, static state uses dataclass fields.
        The code should use hasattr to detect which type of state is used.
        """
        code = generate_python("TEST\n D SUB+1\n Q\nSUB\n S X=1 Q\n")

        # Should check if state has _locals attribute
        assert "hasattr(state, '_locals')" in code

    def test_static_state_uses_setattr(self, generate_python):
        """For static state without _locals, setattr is used to set fields.

        When state doesn't have _locals dict, individual fields must be
        set using setattr.
        """
        code = generate_python("TEST\n D SUB+1\n Q\nSUB\n S X=1 Q\n")

        # Should use setattr for static state
        assert "setattr(state" in code

    def test_marray_values_handled_in_sync(self, generate_python):
        """MArray values are handled correctly during scope sync.

        MArray values should be stored directly, while raw values need
        to be wrapped in MArray for dynamic state.
        """
        code = generate_python("TEST\n D SUB+1\n Q\nSUB\n S X=1 Q\n")

        # Should check if value is MArray
        assert "isinstance(_v, MArray)" in code


@pytest.mark.codegen
class TestGlobalsLookup:
    """Tests for Phase 21: _globals[] lookup instead of direct function name."""

    def test_do_uses_globals_lookup(self, generate_python):
        """D SUB generates _globals['SUB'](...) instead of SUB(...).

        Phase 21: Prevents parameter names from shadowing label names.
        """
        code = generate_python("TEST\n D SUB\n Q\nSUB\n W 1\n Q\n")
        assert "_globals['SUB'](_rt, _scope=_scope)" in code

    def test_do_with_args_uses_globals_lookup(self, generate_python):
        """D SUB(1) generates _globals['SUB'](_rt, 1, _scope=_scope).

        Phase 21: Arguments are passed through the globals lookup.
        """
        code = generate_python("TEST\n D SUB(1)\n Q\nSUB(A)\n W A\n Q\n")
        assert "_globals['SUB'](_rt, 1, _scope=_scope)" in code

    def test_globals_capture_emitted(self, generate_python):
        """Generated code includes _globals = globals() at module level.

        Phase 21: Must capture globals() before any function definitions
        to avoid shadowing.
        """
        code = generate_python("TEST\n Q\n")
        assert "_globals = globals()" in code

    def test_goto_uses_trampoline_dispatch(self, generate_python):
        """G SUB in TRAMPOLINE mode uses _labels dispatch, not direct call.

        GOTO triggers TRAMPOLINE strategy which uses _labels dict for dispatch.
        """
        code = generate_python("TEST\n G SUB\nSUB\n Q\n")
        # TRAMPOLINE uses return (target, state) for dispatch
        assert "return" in code
        assert "SUB" in code

    def test_param_shadowing_label_name(self, execute_mumps):
        """Function A(A,B) where param A shadows label A works correctly.

        Phase 21: This is the key scenario - without _globals[], calling
        A(A,B) from inside B would fail because param A shadows label A.
        """
        result = execute_mumps("TEST\n D B\n Q\nA(A,B)\n W A,B\n Q\nB\n D A(1,2)\n Q\n")
        assert result.output == "12"


@pytest.mark.codegen
class TestDoBlockExtrinsicSave:
    """Tests for Phase 21: DO block saves/restores _in_extrinsic."""

    def test_do_block_saves_extrinsic(self, generate_python):
        """Argumentless DO block generates save/restore of _in_extrinsic.

        Phase 21: $QUIT must be 0 inside DO blocks even if called from
        an extrinsic function context.
        """
        code = generate_python("TEST\n D\n . W 1\n Q\n")
        assert "_saved_extrinsic = _rt._in_extrinsic" in code
        assert "_rt._in_extrinsic = False" in code
        assert "_rt._in_extrinsic = _saved_extrinsic" in code

    def test_do_target_saves_extrinsic(self, generate_python):
        """D SUB generates save/restore of _in_extrinsic for subroutine call.

        Phase 21: Subroutine calls should see $QUIT=0.
        """
        code = generate_python("TEST\n D SUB\n Q\nSUB\n Q\n")
        assert "_saved_extrinsic = _rt._in_extrinsic" in code
        assert "_rt._in_extrinsic = False" in code


@pytest.mark.codegen
class TestByRefMArrayAliasing:
    """Tests for Phase 21: True call-by-reference via MArray aliasing."""

    def test_byref_passes_marray(self, generate_python):
        """D SUB(.X) passes _scope.setdefault('X', MArray()) for aliasing.

        Phase 21: Instead of value-result, pass MArray directly.
        """
        code = generate_python("TEST S X=1 D SUB(.X) Q\nSUB(N) Q\n")
        assert "_scope.setdefault('X', MArray())" in code

    def test_callee_isinstance_check(self, generate_python):
        """Callee generates isinstance(N, MArray) check for by-ref detection.

        Phase 21: Callee detects if param is MArray (by-ref) vs value.
        """
        code = generate_python("TEST S X=1 D SUB(.X) Q\nSUB(N) Q\n")
        assert "if isinstance(N, MArray):" in code
        assert "_scope['N'] = N" in code

    def test_byref_mutation_visible(self, execute_mumps):
        """Mutation through by-ref alias is visible to caller.

        Phase 21: Since caller and callee share the same MArray,
        SET in callee directly modifies caller's variable.
        """
        result = execute_mumps(
            "TEST\n S X=1 D DOUBLE(.X) W X,!\n Q\nDOUBLE(N) S N=N*2 Q\n"
        )
        assert result.output == "2\n"

    def test_byref_with_value_arg_mixed(self, execute_mumps):
        """Mixed by-ref and by-value arguments work correctly.

        D SUB(.X,Y) passes X by-ref (MArray alias) and Y by value.
        """
        result = execute_mumps(
            'TEST\n S X=10,Y=20 D SUB(.X,Y) W X,",",Y,!\n Q\nSUB(A,B) S A=A+B Q\n'
        )
        assert result.output == "30,20\n"


@pytest.mark.codegen
class TestDoExternalRoutineEntryFunction:
    """Phase 24: D ^ROUTINE uses _entry_function for preamble support.

    When a routine has a labelless first line (preamble), the entry function
    is _preamble, not a function named after the routine. Using
    module._entry_function ensures the correct function is called.
    """

    def test_d_routine_generates_entry_function(self, generate_python):
        """D ^MYRTN generates import + call via _entry_function."""
        code = generate_python("TEST D ^MYRTN Q")
        assert "import MYRTN" in code
        assert "MYRTN._entry_function" in code
        # Should NOT hardcode entry label name
        assert "MYRTN.MYRTN" not in code

    def test_d_label_routine_does_not_use_entry_function(self, generate_python):
        """D LABEL^EXTRTN still uses named label, not _entry_function."""
        code = generate_python("TEST D LABEL^EXTRTN Q")
        assert "EXTRTN.LABEL" in code
        # The DO call should reference the label directly, not _entry_function
        # (Note: _entry_function is always declared at module level, so just
        # check the call site doesn't use it)
        for line in code.splitlines():
            if (
                "EXTRTN" in line
                and "import" not in line
                and "_entry_function" not in line
            ):
                if "EXTRTN.LABEL" in line:
                    break
        else:
            pytest.fail("Expected EXTRTN.LABEL call, not _entry_function")


@pytest.mark.codegen
class TestUnwindNewStackInWrapper:
    """Tests for Phase 21: unwind_new_stack() in TRAMPOLINE wrappers."""

    def test_trampoline_wrapper_calls_unwind(self, generate_python):
        """TRAMPOLINE wrapper calls unwind_new_stack(state) before scope sync.

        Phase 21: Ensures NEW variables are restored before state→_scope
        synchronization on subroutine exit.
        """
        # K triggers dynamic_locals, G END triggers TRAMPOLINE
        code = generate_python("TEST K\n G END\n Q\nEND Q\n")
        assert "unwind_new_stack(state)" in code
        assert "from m2py.runtime.helpers import" in code
        assert "unwind_new_stack" in code
