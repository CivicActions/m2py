"""Tests for GOTO command code generation (§8.2.6).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.6
"""

import pytest


@pytest.mark.codegen
class TestGotoCommandCodegen:
    """Codegen-level tests for GOTO command code generation (§8.2.6)."""

    def test_goto_to_function_call(self, generate_python):
        """Simple GOTO generates function call with return (§8.2.6).

        User Story 4 acceptance scenario (T040):
        Given: G DONE
        When: generated
        Then: output contains DONE() and return
        """
        code = generate_python('TEST\n G DONE\n Q\nDONE\n W "END"\n Q\n')
        assert "DONE()" in code
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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: forward jump to if/else")
    def test_forward_jump_to_if_else(self, generate_python):
        """Forward GOTO within label restructures to if/else.

        LABEL S X=1
              G DONE
              S X=2  ; skipped
        DONE  Q X
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: loop continue")
    def test_loop_continue_pattern(self, generate_python):
        """GOTO that continues loop generates continue statement.

        F I=1:1:10 I I#2 G NEXT S X=I
        NEXT ; loop continues here
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: loop exit")
    def test_loop_exit_generates_break(self, generate_python):
        """GOTO that exits loop generates break statement.

        F I=1:1:100 I X>10 G DONE
        DONE ; after loop
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: multi-loop exit")
    def test_multi_loop_exit_generates_exception(self, generate_python):
        """GOTO exiting multiple loops generates exception pattern.

        F I=1:1:10 F J=1:1:10 I X>50 G DONE
        ; exits both loops
        DONE ; after both loops
        """
        pytest.fail("Stub - implement test")


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

        ctx = GotoGenContext.from_statement(stmt, loop_stack=[])
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

        ctx = GotoGenContext.from_statement(stmt, loop_stack=[for_stmt])
        assert ctx.in_for_loop is True
        assert len(ctx.enclosing_loops) == 1

    def test_goto_gen_context_loop_continue(self):
        """GotoGenContext detects loop continue pattern."""
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

        target = MCall(name="NEXT")
        stmt = MGotoStatement(targets=[target])
        # Set analysis flag for loop continue
        stmt.is_loop_continue = True

        ctx = GotoGenContext.from_statement(stmt, loop_stack=[for_stmt])
        assert ctx.pattern == "continue"

    def test_goto_gen_context_single_loop_exit(self):
        """GotoGenContext detects single loop exit pattern."""
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
        # Set analysis flag for loop exit
        stmt.exits_loops = [for_stmt]

        ctx = GotoGenContext.from_statement(stmt, loop_stack=[for_stmt])
        assert ctx.pattern == "break"

    def test_goto_gen_context_multi_loop_exit(self):
        """GotoGenContext detects multi-loop exit pattern."""
        from m2py.asg.elements import MCall, MScope
        from m2py.asg.enums import ForParamType
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
        # Set analysis flag for multi-loop exit
        stmt.exits_loops = [inner_for, outer_for]

        ctx = GotoGenContext.from_statement(stmt, loop_stack=[outer_for, inner_for])
        assert ctx.pattern == "multi_break"

    def test_goto_gen_context_unsupported_external(self):
        """GotoGenContext detects unsupported external GOTO."""
        from m2py.asg.elements import MCall
        from m2py.asg.enums import GotoType
        from m2py.asg.statements import MGotoStatement
        from m2py.codegen.statements import GotoGenContext

        target = MCall(name="EXTERNAL^ROUTINE")
        stmt = MGotoStatement(targets=[target])
        stmt.goto_type = GotoType.EXTERNAL

        ctx = GotoGenContext.from_statement(stmt, loop_stack=[])
        assert ctx.pattern == "unsupported"

    def test_goto_gen_context_unsupported_backward(self):
        """GotoGenContext detects unsupported backward jump."""
        from m2py.asg.elements import MCall
        from m2py.asg.enums import GotoType
        from m2py.asg.statements import MGotoStatement
        from m2py.codegen.statements import GotoGenContext

        target = MCall(name="START")
        stmt = MGotoStatement(targets=[target])
        stmt.goto_type = GotoType.BACKWARD_JUMP

        ctx = GotoGenContext.from_statement(stmt, loop_stack=[])
        assert ctx.pattern == "unsupported"

    def test_goto_gen_context_forward_intra_label(self):
        """GotoGenContext detects intra-label forward jump."""
        from m2py.asg.elements import MCall
        from m2py.asg.enums import GotoType
        from m2py.asg.statements import MGotoStatement
        from m2py.codegen.statements import GotoGenContext

        target = MCall(name="SKIP")
        stmt = MGotoStatement(targets=[target])
        stmt.goto_type = GotoType.FORWARD_JUMP
        stmt.is_cross_label = False

        ctx = GotoGenContext.from_statement(stmt, loop_stack=[])
        assert ctx.pattern == "forward"


@pytest.mark.codegen
class TestIsRestructurableGoto:
    """Tests for _is_restructurable_goto() helper (Spec 005, T028).

    This helper determines if a GOTO can be restructured to if/else.
    """

    def test_intra_label_forward_is_restructurable(self):
        """Intra-label forward GOTO is restructurable.

        When: is_cross_label=False AND goto_type=FORWARD_JUMP
        Then: Returns True - can be restructured to if/else
        """
        from m2py.asg.elements import MCall
        from m2py.asg.enums import GotoType
        from m2py.asg.statements import MGotoStatement
        from m2py.codegen.statements import _is_restructurable_goto

        target = MCall(name="SKIP")
        stmt = MGotoStatement(targets=[target])
        stmt.goto_type = GotoType.FORWARD_JUMP
        stmt.is_cross_label = False

        assert _is_restructurable_goto(stmt) is True

    def test_intra_label_backward_not_restructurable(self):
        """Intra-label backward GOTO is NOT restructurable.

        When: is_cross_label=False AND goto_type=BACKWARD_JUMP
        Then: Returns False - creates implicit loop, needs Spec 006
        """
        from m2py.asg.elements import MCall
        from m2py.asg.enums import GotoType
        from m2py.asg.statements import MGotoStatement
        from m2py.codegen.statements import _is_restructurable_goto

        target = MCall(name="START")
        stmt = MGotoStatement(targets=[target])
        stmt.goto_type = GotoType.BACKWARD_JUMP
        stmt.is_cross_label = False

        assert _is_restructurable_goto(stmt) is False

    def test_cross_label_forward_not_restructurable(self):
        """Cross-label forward GOTO is NOT restructurable.

        When: is_cross_label=True AND goto_type=FORWARD_JUMP
        Then: Returns False - different label, needs function call pattern
        """
        from m2py.asg.elements import MCall
        from m2py.asg.enums import GotoType
        from m2py.asg.statements import MGotoStatement
        from m2py.codegen.statements import _is_restructurable_goto

        target = MCall(name="OTHER")
        stmt = MGotoStatement(targets=[target])
        stmt.goto_type = GotoType.FORWARD_JUMP
        stmt.is_cross_label = True

        assert _is_restructurable_goto(stmt) is False

    def test_loop_exit_not_restructurable(self):
        """LOOP_EXIT GOTO is NOT restructurable (uses break instead).

        When: goto_type=LOOP_EXIT
        Then: Returns False - should generate break, not if/else
        """
        from m2py.asg.elements import MCall
        from m2py.asg.enums import GotoType
        from m2py.asg.statements import MGotoStatement
        from m2py.codegen.statements import _is_restructurable_goto

        target = MCall(name="DONE")
        stmt = MGotoStatement(targets=[target])
        stmt.goto_type = GotoType.LOOP_EXIT
        stmt.is_cross_label = False

        assert _is_restructurable_goto(stmt) is False

    def test_unanalyzed_goto_not_restructurable(self):
        """GOTO without analysis is NOT restructurable.

        When: goto_type is None (analysis not run)
        Then: Returns False - unknown, default to function call
        """
        from m2py.asg.elements import MCall
        from m2py.asg.statements import MGotoStatement
        from m2py.codegen.statements import _is_restructurable_goto

        target = MCall(name="UNKNOWN")
        stmt = MGotoStatement(targets=[target])
        # No goto_type or is_cross_label set

        assert _is_restructurable_goto(stmt) is False


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
