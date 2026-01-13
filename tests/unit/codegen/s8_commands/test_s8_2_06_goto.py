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

    def test_goto_external_routine(self, generate_python):
        """External GOTO G ^ROUTINE generates import and raise GotoExternal (§8.2.6).

        Spec 008 Phase 6: External GOTO raises GotoExternal exception which is
        caught by run_with_goto_support() to transfer control to external routine.
        """
        code = generate_python('TEST\n G ^OTHER\n W "Never"\n Q\n')

        # Should import the external routine
        assert "import OTHER" in code
        # Should import GotoExternal exception
        assert "from m2py.runtime import GotoExternal" in code
        # Should raise GotoExternal with module and None (entry label)
        assert "raise GotoExternal(OTHER, None)" in code
        # "Never" write should be generated but unreachable due to raise
        assert '_rt.write("Never")' in code

    def test_goto_external_label_routine(self, generate_python):
        """External GOTO G LABEL^ROUTINE generates raise with label name (§8.2.6).

        Spec 008 Phase 6: G LABEL^ROUTINE transfers to specific label.
        """
        code = generate_python("TEST\n G HELPER^ext2\n Q\n")

        assert "import ext2" in code
        assert "raise GotoExternal(ext2, 'HELPER')" in code

    def test_goto_external_label_offset(self, generate_python):
        """External GOTO G LABEL+N^ROUTINE generates raise with offset (§8.2.6).

        Spec 008 Phase 6: G LABEL+N^ROUTINE includes offset in GotoExternal.
        """
        code = generate_python("TEST\n G HELPER+2^ext2\n Q\n")

        assert "import ext2" in code
        # Should include offset parameter
        assert "offset=" in code
        assert "GotoExternal(ext2, 'HELPER'" in code

    def test_goto_external_line_offset(self, generate_python):
        """External GOTO G +N^ROUTINE generates raise with line offset (§8.2.6).

        Spec 008 Phase 6: G +N^ROUTINE uses absolute line offset.
        """
        code = generate_python("TEST\n G +5^ext2\n Q\n")

        assert "import ext2" in code
        assert "GotoExternal(ext2, None" in code
        assert "offset=" in code


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

        Note: After Spec 007, intra-label GOTOs with literal offsets may use
        trampoline pattern with offset guards instead of if/else restructuring.
        Both patterns produce correct output.
        """
        code = 'TEST W "A"\n W "B"\n I 1 G TEST+4\n W "C"\n W "D"\n Q\n'
        python_code = generate_python(code)

        # Should NOT contain recursive TEST() call inside the function body
        # The function definition "def TEST(_scope=None):" is expected, but no TEST() calls
        lines = python_code.split("\n")
        in_test_body = False
        for line in lines:
            if "def TEST(_scope=None):" in line:
                in_test_body = True
                continue
            if in_test_body and line.strip().startswith("def "):
                # Hit another function definition, exit TEST body
                break
            if in_test_body:
                assert "TEST()" not in line, f"Found recursive call in: {line}"

        # Should contain either negated condition pattern (simple functions)
        # or offset guard pattern (trampoline with offsets)
        has_restructured_pattern = "if not _test:" in python_code
        has_offset_guard_pattern = "_start_offset" in python_code
        assert has_restructured_pattern or has_offset_guard_pattern, (
            "Expected either if/else restructuring or offset guard pattern"
        )

        # Verify execution produces correct output
        result = execute_mumps(code)
        assert result.output == "ABD"  # C is skipped
        assert result.success is True

    def test_forward_jump_skips_multiple_statements(
        self, generate_python, execute_mumps
    ):
        """Forward GOTO can skip multiple statements.

        Verifies that multiple statements between GOTO and target
        are all wrapped in the if/else block or handled by offset guards.

        Note: After Spec 007, intra-label GOTOs with literal offsets may use
        trampoline pattern with offset guards instead of if/else restructuring.
        """
        code = 'TEST W "A"\n I 1 G TEST+5\n W "B"\n W "C"\n W "D"\n Q\n'
        python_code = generate_python(code)

        # Should contain either negated condition pattern (simple functions)
        # or offset guard pattern (trampoline with offsets)
        has_restructured_pattern = "if not _test:" in python_code
        has_offset_guard_pattern = "_start_offset" in python_code
        assert has_restructured_pattern or has_offset_guard_pattern, (
            "Expected either if/else restructuring or offset guard pattern"
        )

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

    def test_backward_intra_label_goto_generates_while_loop(self, generate_python):
        """Backward intra-label GOTO generates while True pattern (T069a/b).

        Spec 006 Phase 6: Self-loop patterns where a label GOTOs to itself
        are now supported. The label body is wrapped in `while True:` and
        the GOTO becomes `continue`.
        """
        # Self-loop pattern: LOOP GOTOs back to itself
        code = 'TEST W "A"\n I 1 G TEST\n W "B"\n Q\n'
        python_code = generate_python(code)

        # Should generate while True: pattern for self-loop
        assert "while True:" in python_code
        # GOTO TEST from within TEST should become continue
        assert "continue" in python_code
        # QUIT at end should become break
        assert "break" in python_code

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

    def test_if_statement_restructurable_goto_backref(self):
        """MIfStatement.restructurable_goto is set by classify_gotos.

        When an IF statement contains a restructurable forward GOTO in its
        then_scope, the back-reference is set during analysis to avoid
        scanning at codegen time.
        """
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        # IF with forward GOTO that can be restructured
        code = 'TEST W "A"\n I 1 G TEST+3\n W "B"\n Q\n'
        routine = parser.parse(code)
        parser.resolve_references(routine)
        parser.classify_gotos(routine)

        # Find the IF statement
        label = routine.labels[0]
        if_stmt = None
        for stmt in label.body.statements:
            from m2py.asg.statements import MIfStatement

            if isinstance(stmt, MIfStatement):
                if_stmt = stmt
                break

        assert if_stmt is not None, "IF statement not found"
        assert if_stmt.restructurable_goto is not None
        assert if_stmt.restructurable_goto.is_restructurable is True

    def test_if_statement_no_backref_for_cross_label_goto(self):
        """MIfStatement.restructurable_goto is None for cross-label GOTOs.

        Cross-label GOTOs are not restructurable to if/else, so the
        back-reference should not be set.
        """
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        # IF with cross-label GOTO (to different label)
        code = 'TEST I 1 G DONE\n Q\nDONE W "X"\n Q\n'
        routine = parser.parse(code)
        parser.resolve_references(routine)
        parser.classify_gotos(routine)

        # Find the IF statement
        label = routine.labels[0]
        if_stmt = None
        for stmt in label.body.statements:
            from m2py.asg.statements import MIfStatement

            if isinstance(stmt, MIfStatement):
                if_stmt = stmt
                break

        assert if_stmt is not None, "IF statement not found"
        # Cross-label GOTO is not restructurable, so no back-reference
        assert if_stmt.restructurable_goto is None


@pytest.mark.codegen
class TestCrossLabelGotoCodegen:
    """Codegen tests for cross-label GOTO (between different labels).

    These require either labels-as-functions with trampoline or
    state machine fallback depending on complexity.

    Reference: §8.2.6
    """

    def test_cross_label_forward_jump(self, execute_mumps):
        """Cross-label forward GOTO jumps to later label.

        LABEL1 S X=1
               G LABEL2  ; jump to different label
               Q
        LABEL2 W X
               Q
        """
        result = execute_mumps(
            """LABEL1 S X=1
 G LABEL2
 Q
LABEL2 W X
 Q"""
        )
        assert result.output == "1"
        assert result.success is True

    def test_cross_label_backward_jump(self, execute_mumps):
        """Cross-label backward GOTO creates implicit loop via trampoline.

        TEST -> LOOP -> INC -> LOOP (cycle)
        """
        result = execute_mumps(
            """TEST S X=0 G LOOP
INC S X=X+1 W X
LOOP I X<3 G INC
 Q"""
        )
        assert result.output == "123"
        assert result.success is True

    def test_variable_visibility_across_labels(self, execute_mumps):
        """Variables set in one label visible in another via RoutineState.

        LABEL1 S X=1
               G LABEL2
        LABEL2 W X  ; X should be visible
        """
        result = execute_mumps(
            """LABEL1 S X=1
 G LABEL2
 Q
LABEL2 W X
 Q"""
        )
        assert result.output == "1"
        assert result.success is True


@pytest.mark.codegen
class TestTrampolinePatternCodegen:
    """Codegen tests for labels-as-functions with trampoline dispatcher.

    When labels are translated to functions, a trampoline pattern prevents
    stack overflow from mutual recursion.

    Reference: §8.2.6
    """

    def test_trampoline_dispatcher(self, generate_python):
        """Cross-label jumps use trampoline dispatcher.

        Labels return next label name, dispatcher loop handles transitions.
        Prevents RecursionError from deep mutual recursion.
        """
        code = generate_python(
            """TEST G NEXT Q
NEXT W "done" Q"""
        )
        # Entry point with trampoline dispatcher
        assert "def TEST(_scope=None):" in code
        # Spec 007: 'target' is now used instead of 'label' to support int line dispatch
        assert "while target is not None:" in code
        assert "func = _labels[target]" in code

    def test_shared_state_class(self, generate_python):
        """Labels-as-functions share state via RoutineState class.

        Variables visible across labels stored in shared state object.
        """
        code = generate_python(
            """TEST S X=1 G NEXT Q
NEXT W X Q"""
        )
        # RoutineState class generated with variable fields
        assert "@dataclass" in code
        assert "class RoutineState:" in code
        assert "X: Any = None" in code
        # State used in label functions
        assert "state.X = 1" in code
        assert "state.X)" in code

    def test_label_returns_next_label(self, generate_python):
        """Label function returns name of next label to execute.

        GOTO generates: return ("TARGET_LABEL", state)
        """
        code = generate_python(
            """TEST G DONE Q
DONE W "end" Q"""
        )
        # GOTO generates return with target label string
        assert 'return ("DONE", state)' in code


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

    def test_line_map_generation(self, generate_python):
        """T013: Routine with offset call generates _line_map dict.

        When routine contains G LABEL+N, the generated code includes
        _line_map = {line: (label, offset), ...} for line dispatch.
        """
        source = """TEST G STAR+2 Q
STAR W "0"
 W "1"
 W "2"
 Q"""
        code = generate_python(source)

        # Verify _line_map is present
        assert "_line_map" in code, "Generated code should contain _line_map"
        assert "_line_map: dict[int, tuple[str, int]] = {" in code

        # Verify correct entries
        assert '1: ("TEST", 0),' in code  # Line 1 = TEST label
        assert '2: ("STAR", 0),' in code  # Line 2 = STAR label
        assert '3: ("STAR", 1),' in code  # Line 3 = STAR+1
        assert '4: ("STAR", 2),' in code  # Line 4 = STAR+2
        assert '5: ("STAR", 3),' in code  # Line 5 = STAR+3

    def test_line_map_not_generated_without_offsets(self, generate_python):
        """T013b: Routine without offset calls does NOT generate _line_map.

        Only routines with computed offsets need the line map overhead.
        """
        source = """TEST G NEXT Q
NEXT W "done" Q"""
        code = generate_python(source)

        # Verify _line_map is NOT present (no offset calls)
        assert "_line_map" not in code, (
            "No _line_map should be generated without offset calls"
        )

    def test_line_map_excludes_non_executable_lines(self, generate_python):
        """T014: Comment-only and blank lines are excluded from _line_map.

        Only executable lines with statements are mapped.
        Note: The parser doesn't capture comment-only lines as statements,
        so they are naturally excluded from the line map.
        """
        # This test verifies the basic line map structure works
        # Comment lines are never added to MLabel.body.statements by the parser
        source = """TEST G STAR+1 Q
STAR W "0"
 W "1"
 Q"""
        code = generate_python(source)

        # Verify line map exists and has correct structure
        assert "_line_map" in code
        # Lines 1-4 should be in the map (all executable)
        assert '1: ("TEST", 0),' in code
        assert '2: ("STAR", 0),' in code
        assert '3: ("STAR", 1),' in code
        assert '4: ("STAR", 2),' in code

    def test_literal_offset_goto_skips_lines(self, execute_mumps):
        """T022: G STAR+2 outputs "2" (skips first 2 lines after label).

        Literal offset GOTO dispatches by computed line number.
        """
        source = """TEST G STAR+2 Q
STAR W "0"
 W "1"
 W "2"
 Q"""
        result = execute_mumps(source)
        assert result.output == "2"

    def test_offset_zero_executes_label_line(self, execute_mumps):
        """T023: G STAR+0 executes the label line itself.

        Offset 0 means jump to the label line, equivalent to G STAR.
        """
        source = """TEST G STAR+0 Q
STAR W "X" Q"""
        result = execute_mumps(source)
        assert result.output == "X"

    def test_offset_generates_line_dispatch(self, generate_python):
        """Phase 4: GOTO with offset returns (line_number, state).

        G LABEL+N generates:
        - _target = label_line + int(N)
        - Validation check for invalid offset (Phase 7)
        - return (_target, state)
        """
        source = """TEST G STAR+2 Q
STAR W "0"
 W "1"
 W "2"
 Q"""
        code = generate_python(source)
        # Check that offset call generates line-based dispatch with validation
        # Label STAR is at line 2, so STAR+2 computes: _target = 2 + int(2)
        assert "_target = 2 +" in code
        # Phase 7: Validation check for invalid offset
        assert "if _target not in _line_map:" in code
        assert 'raise ValueError("Entry point STAR+' in code
        # Return uses _target
        assert "return (_target, state)" in code

    def test_offset_targeting_multi_statement_line(self, execute_mumps):
        """Offset targeting multi-statement line executes all statements.

        When offset lands on a line with multiple statements separated by
        spaces, MUMPS executes all statements on that line because line
        is the execution unit.
        """
        source = """TEST G STAR+1 Q
STAR W "A"
 W "B" W "C"
 W "D"
 Q"""
        result = execute_mumps(source)
        # STAR+1 targets line 3 (W "B" W "C"), then continues to line 4
        assert result.output == "BCD"

    # Phase 5: Variable Offset GOTO (T025-T029)

    def test_variable_offset_goto_outputs_correct_line(self, execute_mumps):
        """T026: S N=2 G STAR+N outputs "2".

        Variable offset is evaluated at runtime.
        """
        source = """TEST S N=2 G STAR+N Q
STAR W "0"
 W "1"
 W "2"
 Q"""
        result = execute_mumps(source)
        assert result.output == "2"

    def test_variable_offset_zero_executes_label_line(self, execute_mumps):
        """T027: S N=0 G STAR+N executes label line.

        Variable offset 0 is equivalent to G STAR.
        """
        source = """TEST S N=0 G STAR+N Q
STAR W "X" Q"""
        result = execute_mumps(source)
        assert result.output == "X"

    def test_do_with_variable_offset_in_loop(self, execute_mumps):
        """T028: F N=0:1:2 D LINE+N outputs "ABCBCC".

        DO with variable offset in FOR loop:
        - N=0: D LINE+0 → execute "A", "B", "C", then Q returns
        - N=1: D LINE+1 → execute "B", "C", then Q returns
        - N=2: D LINE+2 → execute "C", then Q returns
        """
        source = """TEST F N=0:1:2 D LINE+N
 Q
LINE W "A"
 W "B"
 W "C"
 Q"""
        result = execute_mumps(source)
        assert result.output == "ABCBCC"

    def test_do_offset_returns_to_caller(self, execute_mumps):
        """T028b: D SUB+2 returns to caller after QUIT.

        DO with offset executes from offset line, then Q returns
        to caller which continues execution.
        """
        source = """TEST D SUB+2 W "after" Q
SUB W "0"
 W "1"
 W "2"
 Q"""
        result = execute_mumps(source)
        assert result.output == "2after"

    def test_do_offset_executes_through_quit(self, execute_mumps):
        """T028c: DO+offset executes from offset through QUIT.

        DO with offset starts at the offset line, executes
        all subsequent statements until QUIT, then returns.
        """
        source = """TEST D LINE+1 W "X" Q
LINE W "0"
 W "1"
 W "2"
 Q"""
        result = execute_mumps(source)
        # LINE+1 starts at W "1", then W "2", then Q returns
        # Caller continues with W "X"
        assert result.output == "12X"

    def test_nested_do_offset_variable_evaluated_at_dispatch_time(self, execute_mumps):
        """Offset variable is evaluated at dispatch time, not modified inside.

        When DO+offset uses a variable for the offset, that variable is
        evaluated at the time of the DO call. Modifications to the variable
        inside the subroutine do not affect the already-computed offset.
        This tests that variable evaluation happens at dispatch time.
        """
        source = """TEST S N=1 D SUB+N W "after" Q
SUB W "0"
 S N=99 W "1"
 W "2"
 Q"""
        result = execute_mumps(source)
        # N=1 at dispatch: SUB+1 starts at S N=99 W "1" (skips W "0")
        # The S N=99 executes but doesn't affect the dispatch
        # Output: "12after" (1, 2, then caller continues)
        assert result.output == "12after"

    # Phase 6: Arithmetic Offset Expressions (T030-T034)

    def test_chained_addition_offset(self, execute_mumps):
        """T031: G STAR+1+1 outputs "2" (chained addition).

        Arithmetic offset expression with chained addition evaluates
        correctly: 1+1=2, so STAR+2 is reached.
        """
        source = """TEST G STAR+1+1 Q
STAR W "0"
 W "1"
 W "2"
 Q"""
        result = execute_mumps(source)
        assert result.output == "2"

    def test_variable_subtraction_offset(self, execute_mumps):
        """T032: G STAR+A-B with A=3, B=1 outputs "2".

        Arithmetic offset expression with variable subtraction:
        A-B = 3-1 = 2, so STAR+2 is reached.
        """
        source = """TEST S A=3,B=1 G STAR+A-B Q
STAR W "0"
 W "1"
 W "2"
 Q"""
        result = execute_mumps(source)
        assert result.output == "2"

    def test_division_offset(self, execute_mumps):
        """T033: G STAR+6/3 outputs "2" (division).

        Arithmetic offset expression with division:
        6/3 = 2, so STAR+2 is reached.
        """
        source = """TEST G STAR+6/3 Q
STAR W "0"
 W "1"
 W "2"
 Q"""
        result = execute_mumps(source)
        assert result.output == "2"

    # Phase 7: Invalid Offset Error Handling (T035-T040)

    def test_invalid_literal_offset_raises_error(self, execute_mumps):
        """T038: G STAR+100 raises error (literal offset past end).

        When offset is beyond the routine's end, a ValueError is raised
        with message "Entry point LABEL+OFFSET not valid".
        """
        source = """TEST G STAR+100 Q
STAR W "X" Q"""
        result = execute_mumps(source)
        assert result.success is False
        assert "Entry point STAR+100 not valid" in result.error

    def test_invalid_variable_offset_raises_error(self, execute_mumps):
        """T039: S N=99 G STAR+N raises error at runtime.

        Variable offset that evaluates to invalid value at runtime
        raises error with computed offset value in message.
        """
        source = """TEST S N=99 G STAR+N Q
STAR W "X" Q"""
        result = execute_mumps(source)
        assert result.success is False
        assert "Entry point STAR+99 not valid" in result.error

    def test_invalid_do_offset_raises_error(self, execute_mumps):
        """T038 extension: D SUB+100 raises error (DO offset past end).

        DO with invalid offset also raises error matching YDB behavior.
        """
        source = """TEST D SUB+100 W "after" Q
SUB W "X" Q"""
        result = execute_mumps(source)
        assert result.success is False
        assert "Entry point SUB+100 not valid" in result.error

    def test_negative_offset_raises_error(self, execute_mumps):
        """Negative offset raises error (must resolve to non-negative integer).

        Per data-model.md validation rules, offset must resolve to a
        non-negative integer. Negative offsets raise ValueError at runtime.
        """
        source = """TEST S N=-1 G STAR+N Q
STAR W "0"
 W "1"
 Q"""
        result = execute_mumps(source)
        assert result.success is False
        assert "Entry point STAR+-1 not valid" in result.error

    def test_negative_do_offset_raises_error(self, execute_mumps):
        """Negative DO offset raises error (must resolve to non-negative integer).

        DO with negative offset also raises error matching GOTO behavior.
        """
        source = """TEST S N=-2 D SUB+N W "after" Q
SUB W "0"
 W "1"
 Q"""
        result = execute_mumps(source)
        assert result.success is False
        assert "Entry point SUB+-2 not valid" in result.error

    # Phase 8: Non-Integer Offset Coercion (T041-T044)

    def test_float_offset_truncated(self, execute_mumps):
        """T042: G STAR+2.7 outputs "2" (float truncated).

        Non-integer offset is truncated to integer using Python's int().
        2.7 truncates to 2, so STAR+2 is reached.
        """
        source = """TEST G STAR+2.7 Q
STAR W "0"
 W "1"
 W "2"
 Q"""
        result = execute_mumps(source)
        assert result.output == "2"

    def test_float_offset_floor_toward_zero(self, execute_mumps):
        """T043: G STAR+2.999 outputs "2" (floor toward zero).

        Non-integer offset near next integer still truncates down.
        2.999 truncates to 2, not rounds to 3.
        """
        source = """TEST G STAR+2.999 Q
STAR W "0"
 W "1"
 W "2"
 Q"""
        result = execute_mumps(source)
        assert result.output == "2"

    def test_string_offset_coerces_to_zero(self, execute_mumps):
        """String offset coerces to 0 (standard numeric coercion).

        When offset expression evaluates to a non-numeric string like "ABC",
        MUMPS numeric coercion rules convert it to 0. So G STAR+X where
        X="ABC" is equivalent to G STAR+0 (executes label line).
        """
        source = """TEST S X="ABC" G STAR+X Q
STAR W "0"
 W "1"
 W "2"
 Q"""
        result = execute_mumps(source)
        # "ABC" coerces to 0, so STAR+0 = label line outputs "0", then "1", "2"
        assert result.output == "012"

    # Phase 9: Comment/Blank Line Handling (T045-T049)

    def test_offset_landing_on_comment_continues(self, execute_mumps):
        """T047: Offset landing on comment line continues to next executable.

        When GOTO offset lands on a comment line (not in _line_map),
        execution continues to the next executable line.
        """
        source = """TEST G STAR+1 Q
STAR W "0"
;comment line
 W "2"
 Q"""
        result = execute_mumps(source)
        assert result.output == "2"

    def test_offset_landing_on_blank_continues(self, execute_mumps):
        """T048: Offset landing on blank line continues to next executable.

        When GOTO offset lands on a blank line (not in _line_map),
        execution continues to the next executable line.
        """
        source = """TEST G STAR+1 Q
STAR W "0"

 W "2"
 Q"""
        result = execute_mumps(source)
        assert result.output == "2"

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: same level enforcement")
    def test_same_level_enforcement(self, generate_python):
        """GOTO must target same execution LEVEL.

        Per ANSI, GOTO to different level raises M45 error.
        """
        pytest.fail("Stub - implement test")
