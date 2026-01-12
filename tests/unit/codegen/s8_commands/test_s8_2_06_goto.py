"""Tests for GOTO command code generation (§8.2.6).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.6
"""

import pytest


@pytest.mark.codegen
class TestGotoCommandCodegen:
    """Codegen-level tests for GOTO command code generation (§8.2.6)."""

    def test_goto_to_function_call(self, generate_python):
        """Simple cross-label GOTO generates trampoline pattern (§8.2.6).

        User Story 4 acceptance scenario (T040):
        Given: G DONE (cross-label)
        When: generated
        Then: output contains return ("DONE", state) for trampoline pattern
        """
        code = generate_python('TEST\n G DONE\n Q\nDONE\n W "END"\n Q\n')
        # Cross-label GOTO uses trampoline pattern with label string
        assert 'return ("DONE", state)' in code
        assert "return" in code

    def test_goto_transfers_control(self, execute_mumps):
        """GOTO transfers control to target label.

        User Story 4 acceptance scenario (T041):
        Given: TEST G END Q END W "END" Q
        When: generated and executed
        Then: output is "END"
        """
        result = execute_mumps('TEST\n G END\n Q\nEND\n W "END"\n Q\n')
        assert result.output == "END"
        assert result.success is True

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: GOTO computed")
    def test_goto_computed(self, generate_python):
        """Computed GOTO generates dispatch table (§8.2.6)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: GOTO external")
    def test_goto_external(self, generate_python):
        """External GOTO generates import and call (§8.2.6)."""
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestIntraLabelGotoCodegen:
    """Codegen tests for intra-label GOTO (within same label).

    These can often be restructured to if/else, continue, or break.

    Reference: §8.2.6
    """

    def test_forward_jump_restructures_to_if_else(self, generate_python, execute_mumps):
        """Forward GOTO within label restructures to if/else (T032).

        Verifies that intra-label forward GOTOs are transformed into
        if/else blocks rather than recursive function calls.

        MUMPS:  I 1 G TEST+4  ; if true, skip to W "D"
                W "C"          ; skipped when GOTO fires
                W "D"          ; target
                Q

        Python: _test = m_truth(1)
                if not _test:
                    _rt.write(str("C"))  # only when condition false
                _rt.write(str("D"))  # always executed
        """
        code = 'TEST W "A"\n W "B"\n I 1 G TEST+4\n W "C"\n W "D"\n Q\n'
        python_code = generate_python(code)

        # Should NOT contain recursive TEST() call inside the function body
        # The function definition "def TEST():" is expected, but no TEST() calls
        lines = python_code.split("\n")
        in_test_body = False
        for line in lines:
            if "def TEST():" in line:
                in_test_body = True
                continue
            if in_test_body and line.strip().startswith("def "):
                # Hit another function definition, exit TEST body
                break
            if in_test_body:
                assert "TEST()" not in line, f"Found recursive call in: {line}"

        # Should contain the negated condition pattern
        assert "if not _test:" in python_code

        # Verify execution produces correct output
        result = execute_mumps(code)
        assert result.output == "ABD"  # C is skipped
        assert result.success is True

    def test_forward_jump_skips_multiple_statements(
        self, generate_python, execute_mumps
    ):
        """Forward GOTO can skip multiple statements.

        Verifies that multiple statements between GOTO and target
        are all wrapped in the if/else block.
        """
        code = 'TEST W "A"\n I 1 G TEST+5\n W "B"\n W "C"\n W "D"\n Q\n'
        python_code = generate_python(code)

        # Should contain negated condition
        assert "if not _test:" in python_code

        # Verify execution - all of B, C, D skipped
        result = execute_mumps(code)
        assert result.output == "A"  # B, C, D skipped, then QUIT
        assert result.success is True

    def test_forward_jump_condition_false_executes_skipped(
        self, generate_python, execute_mumps
    ):
        """When condition is false, GOTO doesn't fire and skipped statements execute.

        Verifies that the restructuring correctly handles the false case.
        """
        code = 'TEST W "A"\n W "B"\n I 0 G TEST+4\n W "C"\n W "D"\n Q\n'
        _python_code = generate_python(code)  # noqa: F841 - verify generation succeeds

        # Verify execution - condition false means C is NOT skipped
        result = execute_mumps(code)
        assert result.output == "ABCD"  # C is executed when condition is false
        assert result.success is True

    def test_backward_intra_label_goto_raises_error(self, generate_python):
        """Backward intra-label GOTO raises UnsupportedFeatureError (T033).

        Backward GOTOs within a label create implicit loops that cannot
        be restructured to simple if/else. These require Spec 006.
        """
        from m2py.codegen.statements import UnsupportedFeatureError

        code = 'TEST W "A"\n I 1 G TEST\n W "B"\n Q\n'
        with pytest.raises(UnsupportedFeatureError, match="Backward intra-label GOTO"):
            generate_python(code)

    def test_goto_cannot_create_continue_pattern(self, generate_python):
        """GOTO cannot create Python continue pattern (T039 - updated).

        Per MUMPS spec (MDC 3.6.5): "Execution of GOTO effects the immediate
        termination of all FORs in the line containing the GOTO."

        A GOTO to the same label from inside a FOR loop:
        1. Terminates the FOR loop
        2. Jumps to the label (function call/recursion)

        There is NO "continue" pattern via GOTO - use conditional execution
        (I cond <commands>) or QUIT from a DO block for skip-iteration behavior.
        """
        # This GOTO exits the FOR loop and calls TEST - it does NOT continue
        # In YDB, this creates infinite recursion until stack overflow
        code = """TEST S X=""
 F I=1:1:5 D
 . I I#2=0 G TEST
 . S X=X_I
 W X
 Q
"""
        python_code = generate_python(code)

        # The GOTO should generate break (exits loop) not continue
        # The generated code should have 'break' or function call pattern
        assert "continue" not in python_code
        # The FOR loop should still have break support for the GOTO exit
        assert "break" in python_code

    def test_loop_exit_generates_break(self, generate_python):
        """GOTO that exits loop generates break statement (T040).

        When a GOTO inside a single FOR loop targets a label after
        the loop, it should generate 'break' to exit the loop.

        FR-018: Cross-label exits must call the target after loop exit.
        """
        # MUMPS: exit loop when I > 5, then write I
        code = """TEST F I=1:1:100 I I>5 G DONE
DONE W I
 Q
"""
        python_code = generate_python(code)

        # The loop exit GOTO should generate 'break'
        assert "break" in python_code
        # Look for the break in the context of the _TEST function (trampoline label function)
        test_func = python_code.split("def _TEST(state)")[1].split("def _DONE(state)")[
            0
        ]
        assert "break" in test_func
        # FR-018: Cross-label exit should track target label as string
        assert '_goto_label = "DONE"' in test_func
        # FR-018: After loop, return to trampoline with target label
        assert "return (_goto_label, state)" in test_func

    def test_multi_loop_exit_generates_exception(self, generate_python):
        """GOTO exiting multiple loops generates exception pattern (T041).

        When a GOTO inside nested FOR loops needs to exit both loops,
        it should generate 'raise _LoopExit(target)' and the outermost loop
        should be wrapped in try/except _LoopExit.

        FR-018: Cross-label exits should pass target label string to exception.
        """
        # MUMPS: exit both loops when I*J > 15
        code = """TEST S X=0
 F I=1:1:10 F J=1:1:10 I I*J>15 G DONE
DONE W I*J
 Q
"""
        python_code = generate_python(code)

        # Should generate the _LoopExit exception class
        assert "class _LoopExit" in python_code
        # FR-018: Cross-label multi-loop exit should pass target label string
        assert 'raise _LoopExit("DONE")' in python_code
        # Outer loop should have try/except wrapper
        assert "try:" in python_code
        assert "except _LoopExit" in python_code
        # FR-018: except block should return target to trampoline
        assert "return (_e.target, state)" in python_code

    def test_single_loop_exit_executes_target_label(self, execute_mumps):
        """FR-018: Single loop exit GOTO calls target label code (T077).

        When GOTO exits a single loop, it should break from the loop
        AND then call the target label so its code runs.
        """
        # MUMPS: exit loop when I > 5, DONE writes "!"
        result = execute_mumps(
            'TEST\n F I=1:1:10 W I I I>5 G DONE\n Q\nDONE\n W "!"\n Q\n'
        )
        # Should print 1-6 then "!" (not just 1-6)
        assert result.output == "123456!"
        assert result.success is True

    def test_multi_loop_exit_executes_target_label(self, execute_mumps):
        """FR-018: Multi-loop exit GOTO calls target label code (T078).

        When GOTO exits multiple nested loops, it should break from all
        AND then call the target label so its code runs.
        """
        # MUMPS: exit both loops when I*J > 15, OUT writes "X"
        # With I,J in 1:5, the condition triggers at I=4,J=4 (16>15)
        result = execute_mumps(
            'TEST\n F I=1:1:5 F J=1:1:5 W I,J I I*J>15 G OUT\n Q\nOUT\n W "X"\n Q\n'
        )
        # All IJ pairs where I*J <= 15 print, then 4*4=16 triggers GOTO to OUT
        # Pairs: 11,12,13,14,15, 21,22,23,24,25, 31,32,33,34,35, 41,42,43,44 then X
        assert result.output == "11121314152122232425313233343541424344X"
        assert result.success is True


@pytest.mark.codegen
class TestGotoGenContextCodegen:
    """Tests for GotoGenContext helper dataclass (Spec 005)."""

    def test_goto_gen_context_from_simple_statement(self):
        """GotoGenContext correctly analyzes simple GOTO."""
        from m2py.asg.elements import MCall
        from m2py.asg.statements import MGotoStatement
        from m2py.codegen.statements import GotoGenContext

        target = MCall(name="DONE")
        stmt = MGotoStatement(targets=[target])

        ctx = GotoGenContext.from_statement(stmt)
        assert ctx.target_label == "DONE"
        assert ctx.in_for_loop is False
        assert ctx.pattern == "function_call"

    def test_goto_gen_context_in_for_loop(self):
        """GotoGenContext detects GOTO inside FOR loop."""
        from m2py.asg.elements import MCall, MScope
        from m2py.asg.enums import ForParamType
        from m2py.asg.expressions import MLiteral
        from m2py.asg.statements import MForParameter, MForStatement, MGotoStatement
        from m2py.codegen.statements import GotoGenContext

        # Create a FOR statement
        param = MForParameter(
            param_type=ForParamType.RANGE,
            start=MLiteral(value=1),
            step=MLiteral(value=1),
            end=MLiteral(value=10),
        )
        for_stmt = MForStatement(
            loop_var="I",
            parameters=[param],
            body=MScope(statements=[]),
        )

        target = MCall(name="DONE")
        stmt = MGotoStatement(targets=[target])
        # Set exits_loops on stmt (would be set by analysis in real code)
        stmt.exits_loops = [for_stmt]

        ctx = GotoGenContext.from_statement(stmt)
        assert ctx.in_for_loop is True
        assert len(ctx.enclosing_loops) == 1

    def test_goto_gen_context_no_continue_pattern(self):
        """GotoGenContext does not detect continue pattern (doesn't exist).

        Per MUMPS spec, GOTO cannot create continue semantics - it always
        terminates all FOR loops on the line containing the GOTO.
        """
        from m2py.asg.elements import MCall
        from m2py.asg.statements import MGotoStatement
        from m2py.codegen.statements import GotoGenContext

        target = MCall(name="NEXT")
        stmt = MGotoStatement(targets=[target])
        # Note: There is no is_loop_continue flag - GOTO cannot create continue
        # from_statement() now only takes stmt (loop context comes from ASG fields)

        ctx = GotoGenContext.from_statement(stmt)
        # Without exits_loops set, it's just a function call
        assert ctx.pattern == "function_call"
        # Verify "continue" is not a valid pattern
        assert ctx.pattern != "continue"

    def test_goto_gen_context_single_loop_exit(self):
        """GotoGenContext detects single loop exit pattern."""
        from m2py.asg.elements import MCall, MScope
        from m2py.asg.enums import ForParamType, GotoCodegenPattern
        from m2py.asg.expressions import MLiteral
        from m2py.asg.statements import MForParameter, MForStatement, MGotoStatement
        from m2py.codegen.statements import GotoGenContext

        # Create a FOR statement
        param = MForParameter(
            param_type=ForParamType.RANGE,
            start=MLiteral(value=1),
            step=MLiteral(value=1),
            end=MLiteral(value=10),
        )
        for_stmt = MForStatement(
            loop_var="I",
            parameters=[param],
            body=MScope(statements=[]),
        )

        target = MCall(name="DONE")
        stmt = MGotoStatement(targets=[target])
        # Set analysis fields - now requires codegen_pattern
        stmt.exits_loops = [for_stmt]
        stmt.codegen_pattern = GotoCodegenPattern.BREAK

        ctx = GotoGenContext.from_statement(stmt)
        assert ctx.pattern == "break"

    def test_goto_gen_context_multi_loop_exit(self):
        """GotoGenContext detects multi-loop exit pattern."""
        from m2py.asg.elements import MCall, MScope
        from m2py.asg.enums import ForParamType, GotoCodegenPattern
        from m2py.asg.expressions import MLiteral
        from m2py.asg.statements import MForParameter, MForStatement, MGotoStatement
        from m2py.codegen.statements import GotoGenContext

        # Create two FOR statements
        param = MForParameter(
            param_type=ForParamType.RANGE,
            start=MLiteral(value=1),
            step=MLiteral(value=1),
            end=MLiteral(value=10),
        )
        outer_for = MForStatement(
            loop_var="I",
            parameters=[param],
            body=MScope(statements=[]),
        )
        inner_for = MForStatement(
            loop_var="J",
            parameters=[param],
            body=MScope(statements=[]),
        )

        target = MCall(name="DONE")
        stmt = MGotoStatement(targets=[target])
        # Set analysis fields - now requires codegen_pattern
        stmt.exits_loops = [inner_for, outer_for]
        stmt.codegen_pattern = GotoCodegenPattern.MULTI_BREAK

        ctx = GotoGenContext.from_statement(stmt)
        assert ctx.pattern == "multi_break"

    def test_goto_gen_context_unsupported_external(self):
        """GotoGenContext detects unsupported external GOTO."""
        from m2py.asg.elements import MCall
        from m2py.asg.enums import GotoCodegenPattern, GotoType
        from m2py.asg.statements import MGotoStatement
        from m2py.codegen.statements import GotoGenContext

        target = MCall(name="EXTERNAL^ROUTINE")
        stmt = MGotoStatement(targets=[target])
        stmt.goto_type = GotoType.EXTERNAL
        stmt.codegen_pattern = GotoCodegenPattern.UNSUPPORTED

        ctx = GotoGenContext.from_statement(stmt)
        assert ctx.pattern == "unsupported"

    def test_goto_gen_context_unsupported_backward(self):
        """GotoGenContext detects unsupported backward jump."""
        from m2py.asg.elements import MCall
        from m2py.asg.enums import GotoCodegenPattern, GotoType
        from m2py.asg.statements import MGotoStatement
        from m2py.codegen.statements import GotoGenContext

        target = MCall(name="START")
        stmt = MGotoStatement(targets=[target])
        stmt.goto_type = GotoType.BACKWARD_JUMP
        stmt.codegen_pattern = GotoCodegenPattern.UNSUPPORTED

        ctx = GotoGenContext.from_statement(stmt)
        assert ctx.pattern == "unsupported"

    def test_goto_gen_context_forward_intra_label(self):
        """GotoGenContext detects intra-label forward jump."""
        from m2py.asg.elements import MCall
        from m2py.asg.enums import GotoCodegenPattern, GotoType
        from m2py.asg.statements import MGotoStatement
        from m2py.codegen.statements import GotoGenContext

        target = MCall(name="SKIP")
        stmt = MGotoStatement(targets=[target])
        stmt.goto_type = GotoType.FORWARD_JUMP
        stmt.is_cross_label = False
        stmt.codegen_pattern = GotoCodegenPattern.FORWARD

        ctx = GotoGenContext.from_statement(stmt)
        assert ctx.pattern == "forward"


@pytest.mark.codegen
class TestIsRestructurableField:
    """Tests for MGotoStatement.is_restructurable field (Spec 005, T028).

    This field is populated by _compute_codegen_fields() in goto_analysis.py
    and determines if a GOTO can be restructured to if/else.
    Note: Phase 14 refactoring moved this logic from codegen to analysis layer.
    """

    def test_intra_label_forward_is_restructurable(self):
        """Intra-label forward GOTO is restructurable.

        When: is_cross_label=False AND goto_type=FORWARD_JUMP
        Then: is_restructurable=True - can be restructured to if/else
        """
        from m2py.asg.elements import MCall
        from m2py.asg.enums import GotoType
        from m2py.asg.statements import MGotoStatement
        from m2py.analysis.goto_analysis import _compute_codegen_fields

        target = MCall(name="SKIP")
        stmt = MGotoStatement(targets=[target])
        stmt.goto_type = GotoType.FORWARD_JUMP
        stmt.is_cross_label = False
        _compute_codegen_fields(stmt)

        assert stmt.is_restructurable is True

    def test_intra_label_backward_not_restructurable(self):
        """Intra-label backward GOTO is NOT restructurable.

        When: is_cross_label=False AND goto_type=BACKWARD_JUMP
        Then: is_restructurable=False - creates implicit loop, needs Spec 006
        """
        from m2py.asg.elements import MCall
        from m2py.asg.enums import GotoType
        from m2py.asg.statements import MGotoStatement
        from m2py.analysis.goto_analysis import _compute_codegen_fields

        target = MCall(name="START")
        stmt = MGotoStatement(targets=[target])
        stmt.goto_type = GotoType.BACKWARD_JUMP
        stmt.is_cross_label = False
        _compute_codegen_fields(stmt)

        assert stmt.is_restructurable is False

    def test_cross_label_forward_not_restructurable(self):
        """Cross-label forward GOTO is NOT restructurable.

        When: is_cross_label=True AND goto_type=FORWARD_JUMP
        Then: is_restructurable=False - different label, needs function call pattern
        """
        from m2py.asg.elements import MCall
        from m2py.asg.enums import GotoType
        from m2py.asg.statements import MGotoStatement
        from m2py.analysis.goto_analysis import _compute_codegen_fields

        target = MCall(name="OTHER")
        stmt = MGotoStatement(targets=[target])
        stmt.goto_type = GotoType.FORWARD_JUMP
        stmt.is_cross_label = True
        _compute_codegen_fields(stmt)

        assert stmt.is_restructurable is False

    def test_loop_exit_not_restructurable(self):
        """LOOP_EXIT GOTO is NOT restructurable (uses break instead).

        When: goto_type=LOOP_EXIT
        Then: is_restructurable=False - should generate break, not if/else
        """
        from m2py.asg.elements import MCall
        from m2py.asg.enums import GotoType
        from m2py.asg.statements import MGotoStatement
        from m2py.analysis.goto_analysis import _compute_codegen_fields

        target = MCall(name="DONE")
        stmt = MGotoStatement(targets=[target])
        stmt.goto_type = GotoType.LOOP_EXIT
        stmt.is_cross_label = False
        _compute_codegen_fields(stmt)

        assert stmt.is_restructurable is False

    def test_unanalyzed_goto_not_restructurable(self):
        """GOTO without analysis is NOT restructurable.

        When: goto_type is None (analysis not run)
        Then: is_restructurable=False - unknown, default to function call
        """
        from m2py.asg.elements import MCall
        from m2py.asg.statements import MGotoStatement
        from m2py.analysis.goto_analysis import _compute_codegen_fields

        target = MCall(name="UNKNOWN")
        stmt = MGotoStatement(targets=[target])
        # No goto_type or is_cross_label set
        _compute_codegen_fields(stmt)

        assert stmt.is_restructurable is False


@pytest.mark.codegen
class TestCrossLabelGotoCodegen:
    """Codegen tests for cross-label GOTO (between different labels).

    These require either labels-as-functions with trampoline or
    state machine fallback depending on complexity.

    Reference: §8.2.6
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: cross-label forward jump")
    def test_cross_label_forward_jump(self, generate_python):
        """Cross-label forward GOTO jumps to later label.

        LABEL1 S X=1
               G LABEL2  ; jump to different label
               Q
        LABEL2 S Y=2
               Q
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: cross-label backward jump")
    def test_cross_label_backward_jump(self, generate_python):
        """Cross-label backward GOTO creates implicit loop.

        LABEL1 S X=X+1
               I X<10 G LABEL2
               Q
        LABEL2 G LABEL1  ; loop back
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: variable visibility across labels")
    def test_variable_visibility_across_labels(self, generate_python):
        """Variables set in one label visible in another.

        LABEL1 S X=1
               G LABEL2
        LABEL2 W X  ; X should be visible
        """
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestTrampolinePatternCodegen:
    """Codegen tests for labels-as-functions with trampoline dispatcher.

    When labels are translated to functions, a trampoline pattern prevents
    stack overflow from mutual recursion.

    Reference: §8.2.6
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: trampoline dispatcher")
    def test_trampoline_dispatcher(self, generate_python):
        """Cross-label jumps use trampoline dispatcher.

        Labels return next label name, dispatcher loop handles transitions.
        Prevents RecursionError from deep mutual recursion.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: shared state class")
    def test_shared_state_class(self, generate_python):
        """Labels-as-functions share state via RoutineState class.

        Variables visible across labels stored in shared state object.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: label returns next label")
    def test_label_returns_next_label(self, generate_python):
        """Label function returns name of next label to execute.

        GOTO generates: return 'TARGET_LABEL'
        """
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestStateMachineCodegen:
    """Codegen tests for state machine fallback pattern.

    When control flow is truly unstructured (has_unstructured_goto=True),
    fall back to a state machine with match-case.

    Reference: §8.2.6
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: state machine fallback")
    def test_state_machine_fallback(self, generate_python):
        """Unstructured routines use state machine pattern.

        match state:
            case 'LABEL1': ...
            case 'LABEL2': ...
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: state machine variable scope")
    def test_state_machine_variable_scope(self, generate_python):
        """State machine keeps all variables in outer scope.

        Variables naturally visible across all states.
        """
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestLineDispatchCodegen:
    """Codegen tests for line-based dispatch (for computed offsets).

    Line dispatch maps source line numbers to entry points for handling
    computed offset targets like G LABEL+expr.

    Reference: §8.2.6
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: line map generation")
    def test_line_map_generation(self, generate_python):
        """Routine generates line-to-entry-point mapping.

        _line_map = {1: _line_1, 5: _line_5, ...}
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: line dispatch call")
    def test_line_dispatch_call(self, generate_python):
        """GOTO with offset dispatches by computed line.

        G LABEL+N generates: _goto_line(label_line + N)
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: same level enforcement")
    def test_same_level_enforcement(self, generate_python):
        """GOTO must target same execution LEVEL.

        Per ANSI, GOTO to different level raises M45 error.
        """
        pytest.fail("Stub - implement test")
