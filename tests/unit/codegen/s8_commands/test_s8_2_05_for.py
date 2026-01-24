"""Tests for FOR command code generation (§8.2.5).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.5
"""

import pytest


@pytest.mark.codegen
class TestForCommandCodegen:
    """Codegen-level tests for FOR command code generation (§8.2.5)."""

    def test_for_counted_to_while(self, generate_python):
        """FOR counted generates Python while loop (§8.2.5).

        We use while loops instead of range() to support non-integer steps.
        MUMPS allows F I=.001:.01:1 which would fail with Python's range().
        """
        code = generate_python("TEST\n F I=1:1:3 W I\n Q\n")
        assert "while (" in code
        assert "_for_step" in code
        assert "_for_end" in code

    def test_for_list_to_for_in(self, generate_python):
        """FOR list generates Python for-in loop (§8.2.5)."""
        code = generate_python('TEST\n F I="A","B","C" W I\n Q\n')
        assert 'for I in ["A", "B", "C"]:' in code

    def test_for_bounded_iteration(self, execute_mumps):
        """FOR bounded range outputs correct values.

        User Story 3 acceptance scenario 1 (T036):
        Given: F I=1:1:3 W I
        When: generated and executed
        Then: output is "123" (end-inclusive)
        """
        result = execute_mumps("TEST\n F I=1:1:3 W I\n Q\n")
        assert result.output == "123"
        assert result.success is True

    def test_for_decrement_iteration(self, execute_mumps):
        """FOR decrement range outputs correct values.

        User Story 3 acceptance scenario 2 (T037):
        Given: F I=5:-1:3 W I
        When: generated and executed
        Then: output is "543" (end-inclusive, negative step)
        """
        result = execute_mumps("TEST\n F I=5:-1:3 W I\n Q\n")
        assert result.output == "543"
        assert result.success is True

    def test_for_string_list_iteration(self, execute_mumps):
        """FOR string list outputs correct values.

        User Story 3 acceptance scenario 3 (T038):
        Given: F I="A","B","C" W I
        When: generated and executed
        Then: output is "ABC"
        """
        result = execute_mumps('TEST\n F I="A","B","C" W I\n Q\n')
        assert result.output == "ABC"
        assert result.success is True

    def test_for_open_ended_with_quit(self, generate_python):
        """FOR open-ended generates itertools.count loop with QUIT (§8.2.5).

        T023: Open-ended FOR with QUIT
        Given: F I=1:1 W I Q:I=5
        When: generated
        Then: uses itertools.count and has conditional exit
        """
        code = generate_python("TEST\n F I=1:1 D\n . W I\n . I I=5 Q\n Q\n")
        assert "from itertools import" in code
        assert "count(" in code
        assert "for I in count(" in code

    def test_for_argumentless_with_do_block(self, generate_python):
        """FOR argumentless generates while True loop (§8.2.5).

        T024: Argumentless FOR with DO block
        Given: F  D ... (with dot-indented body)
        When: generated
        Then: uses while True pattern
        """
        code = generate_python(
            "TEST\n S X=3\n F  D\n . S X=X-1\n . W X\n . I X=0 Q\n Q\n"
        )
        assert "while True:" in code

    def test_for_mixed_parameters(self, execute_mumps):
        """FOR mixed parameters iterates all in order (§8.2.5).

        T025: Mixed parameter FOR
        Given: F I=1:1:3,"X",10:2:14 W I
        When: generated and executed
        Then: output is "123X101214"
        """
        result = execute_mumps('TEST\n F I=1:1:3,"X",10:2:14 W I\n Q\n')
        assert result.output == "123X101214"
        assert result.success is True

    def test_for_loop_var_modification(self, execute_mumps):
        """FOR with modified loop var uses while pattern (§8.2.5).

        T026: FOR with loop var modification
        Given: F I=1:1:10 S I=I+2 W I I I>8 Q
        When: generated and executed
        Then: output is "369" (I=1, set I=3, write, next I=4, set I=6, write, I=7, set I=9, write, I>8 quit)
        """
        result = execute_mumps("TEST\n F I=1:1:10 S I=I+2 W I I I>8 Q\n Q\n")
        assert result.output == "369"
        assert result.success is True

    def test_for_byref_modification_detected(self, execute_mumps):
        """FOR with by-ref modification in callee uses while pattern.

        When a FOR loop passes the loop variable by reference to a subroutine
        that modifies it, the analysis detects this and generates a while loop.
        """
        # MOD(X) adds 10 to X via by-ref, so I goes 1->11 (> end=3)
        result = execute_mumps(
            "TEST\n F I=1:1:3 D MOD(.I) W I,!\n Q\nMOD(X) S X=X+10 Q\n"
        )
        assert result.output == "11\n"
        assert result.success is True

    def test_for_byref_modification_generates_while(self, generate_python):
        """FOR with by-ref modification generates while loop pattern."""
        code = generate_python(
            "TEST\n F I=1:1:3 D MOD(.I) W I\n Q\nMOD(X) S X=X+10 Q\n"
        )
        # Should use while loop because callee modifies loop var via by-ref
        assert "while" in code.lower()

    def test_for_negative_step_bounds(self, execute_mumps):
        """FOR negative step iterates correctly (§8.2.5).

        T027: Negative step FOR bounds
        Given: F I=10:-2:2 W I
        When: generated and executed
        Then: output is "108642" (inclusive end)
        """
        result = execute_mumps("TEST\n F I=10:-2:2 W I\n Q\n")
        assert result.output == "108642"
        assert result.success is True

    def test_for_nested(self, execute_mumps):
        """Nested FOR generates nested Python loops (§8.2.5)."""
        result = execute_mumps("TEST\n F I=1:1:2 F J=1:1:2 W I,J\n Q\n")
        assert result.output == "11122122"
        assert result.success is True

    def test_for_nested_different_ranges(self, execute_mumps):
        """Nested FOR with different step directions iterates correctly (Spec 017).

        Spec 017 Phase 11: Before fix, nested FOR loops were using shared
        variable names (_for_start, _for_step, _for_end) causing the inner
        loop to clobber the outer loop's iteration state.

        Given: F K=-1:1:1 F J=1:-1:-1 (outer: -1,0,1; inner: 1,0,-1)
        When: executed
        Then: total iterations = 3 * 3 = 9
        """
        result = execute_mumps(
            "TEST\n S C=0 F K=-1:1:1 F J=1:-1:-1 S C=C+1\n W C\n Q\n"
        )
        assert result.output == "9"
        assert result.success is True

    def test_for_nested_unique_var_names(self, generate_python):
        """Nested FOR generates unique variable names for each loop (Spec 017).

        Spec 017 Phase 11: Each FOR loop must use unique names for its
        iteration variables (_for_start_N, _for_step_N, _for_end_N) to
        prevent variable collision in nested loops.
        """
        code = generate_python("TEST\n F I=1:1:3 F J=1:1:2 W I,J\n Q\n")
        # Should have two different sets of loop variables (0-indexed)
        assert "_for_start_0" in code or "_for_step_0" in code
        assert "_for_start_1" in code or "_for_step_1" in code

    def test_for_list_lazy_evaluation(self, execute_mumps):
        """FOR list evaluates values lazily at each iteration (Spec 017).

        Spec 017 Phase 11: MUMPS FOR with comma-separated values evaluates
        each value expression at the start of its iteration, not all at once.

        Given: F K="a",K_"b",K_"c" S K=K_"*"
        When: executed
        Then: K is "a*b*c*" (each iteration uses current K value)

        Before fix, all values were pre-computed giving K="0c*" because
        K was undefined (empty) when K_"b" and K_"c" were evaluated.
        """
        result = execute_mumps('TEST\n F K="a",K_"b",K_"c" S K=K_"*"\n W K\n Q\n')
        assert result.output == "a*b*c*"
        assert result.success is True

    def test_routine_named_for_executes(self, execute_mumps):
        """Routine named 'for' (Python keyword) executes correctly (Spec 017).

        Spec 017 Phase 11: When a MUMPS routine is named with a Python keyword
        (like 'for', 'if', 'while'), it gets translated to '_m_for', '_m_if', etc.
        The runtime's entry point finder must recognize these as valid user functions.

        Given: A routine with first label 'for' (a Python keyword)
        When: executed
        Then: the routine runs correctly starting at the 'for' label
        """
        # Use 'for' as label name - translated to _m_for internally
        result = execute_mumps('for\n W "PASS"\n Q\n')
        assert result.output == "PASS"
        assert result.success is True

    def test_for_zero_step(self, execute_mumps):
        """FOR with zero step iterates infinitely at same value (T081).

        Zero step (F I=1:0) creates an infinite loop staying at I=1.
        Loop must be terminated by QUIT.
        """
        result = execute_mumps("TEST\n S C=0\n F I=1:0 S C=C+1 I C>5 Q\n W C\n Q\n")
        assert result.output == "6"
        assert result.success is True

    def test_for_zero_step_with_end(self, execute_mumps):
        """FOR with zero step and end value enters if start <= end (T075).

        F I=4:0:5 - zero step with start=4, end=5
        Loop enters because 4 <= 5, but never increments (step=0)
        Must be terminated by QUIT.

        This tests the fix where step=0 bounded FOR only enters if start <= end.
        """
        result = execute_mumps(
            'TEST\n S C=0\n F I=4:0:5 S C=C+1 I C>3 Q\n W C,"-",I,!\n Q\n'
        )
        # Loop enters 4 times (C=1,2,3,4), exits when C>3 (C=4)
        # I stays at 4 (never increments with step=0)
        assert result.output == "4-4\n"
        assert result.success is True

    def test_for_zero_step_with_end_empty_range(self, execute_mumps):
        """FOR with zero step and start > end never enters (T075).

        F I=6:0:5 - zero step with start=6, end=5
        Loop never enters because 6 > 5 (even though step=0 would infinite loop).
        """
        result = execute_mumps("TEST\n S C=0\n F I=6:0:5 S C=C+1\n W C,!\n Q\n")
        # Loop never enters because start > end
        assert result.output == "0\n"
        assert result.success is True

    def test_for_empty_body(self, generate_python):
        """FOR with no body compiles correctly (T082).

        A FOR loop with an empty body is valid MUMPS (does nothing).
        This can happen when all commands are postconditioned and false.
        """
        code = generate_python("TEST\n F I=1:1:3\n Q\n")
        # Should compile without error
        assert "while (" in code
        # The loop should have pass or minimal body
        assert "pass" in code or "_for_step" in code

    def test_for_single_value_edge(self, execute_mumps):
        """FOR with single string value executes body once (§8.2.5).

        T057: Single-value FOR parameter
        Given: F I="X" W I,!
        When: executed
        Then: output is "X\n" - the string value is iterated once

        Reference: Finding 34 from research.md
        A FOR loop with just a value (no step/end) iterates once with that value.
        """
        result = execute_mumps('TEST\n F I="X" W I,!\n Q\n')
        assert result.output == "X\n"
        assert result.success is True

    def test_for_multi_range_edge(self, execute_mumps):
        """FOR with multiple ranges iterates all in sequence (§8.2.5).

        T058: Multi-range FOR parameters
        Given: F I=1:1:2,3:1:4 W I
        When: executed
        Then: output is "1234" - both ranges are iterated in order

        Reference: Finding 36 from research.md
        Multiple comma-separated range parameters are iterated sequentially.
        """
        result = execute_mumps("TEST\n F I=1:1:2,3:1:4 W I\n Q\n")
        assert result.output == "1234"
        assert result.success is True

    def test_for_empty_range_sets_loop_var(self, execute_mumps):
        """FOR with empty range (start > end for positive step) still sets loop var (Spec 017).

        Spec 017: MUMPS FOR always sets the loop variable to the start value,
        even when the loop body doesn't execute (e.g., F I=2:-1:3 never executes
        because 2 > 3 with step -1).

        Given: S K=99 F K=2:-1:3 W "loop"
        When: executed
        Then: K is set to 2 even though loop doesn't execute (body never runs)
        """
        result = execute_mumps("TEST\n S K=99\n F K=2:-1:3 W K\n W !,K\n Q\n")
        # The loop body (W K) never executes because range is empty
        # But K should be 2 (the start value), not 99
        assert result.output == "\n2"
        assert result.success is True

    def test_for_empty_range_positive_step_sets_loop_var(self, execute_mumps):
        """FOR with empty range (start > end for positive step) sets loop var (Spec 017).

        Given: S K=99 F K=10:1:5 W K
        When: executed
        Then: K is set to 10 even though loop doesn't execute
        """
        result = execute_mumps("TEST\n S K=99\n F K=10:1:5 W K\n W !,K\n Q\n")
        # Loop never executes (10 > 5), but K should be 10
        assert result.output == "\n10"
        assert result.success is True


@pytest.mark.codegen
class TestForGenContextCodegen:
    """Tests for ForGenContext helper dataclass (Spec 005)."""

    def test_for_gen_context_from_bounded_statement(self):
        """ForGenContext correctly analyzes bounded FOR loop."""
        from m2py.asg.enums import ForLoopType, ForParamType
        from m2py.asg.statements import MForParameter, MForStatement
        from m2py.asg.elements import MScope
        from m2py.asg.expressions import MLiteral
        from m2py.codegen.statements import ForGenContext

        # Create a bounded FOR: F I=1:1:10
        param = MForParameter(
            param_type=ForParamType.RANGE,
            start=MLiteral(value=1),
            step=MLiteral(value=1),
            end=MLiteral(value=10),
        )
        stmt = MForStatement(
            loop_var="I",
            parameters=[param],
            body=MScope(statements=[]),
        )
        # Set loop_type (normally set by analyze_for_loops())
        stmt.loop_type = ForLoopType.BOUNDED

        ctx = ForGenContext.from_statement(stmt)
        assert ctx.loop_var == "I"
        assert ctx.loop_type == ForLoopType.BOUNDED
        assert ctx.is_infinite is False

    def test_for_gen_context_from_string_list(self):
        """ForGenContext correctly analyzes string list FOR loop."""
        from m2py.asg.enums import ForLoopType, ForParamType
        from m2py.asg.statements import MForParameter, MForStatement
        from m2py.asg.elements import MScope
        from m2py.asg.expressions import MLiteral
        from m2py.codegen.statements import ForGenContext

        # Create a string list FOR: F I="A","B"
        param = MForParameter(
            param_type=ForParamType.VALUE,
            value=MLiteral(value="A"),
        )
        stmt = MForStatement(
            loop_var="I",
            parameters=[param],
            body=MScope(statements=[]),
        )
        # Set loop_type (normally set by analyze_for_loops())
        stmt.loop_type = ForLoopType.STRING_LIST

        ctx = ForGenContext.from_statement(stmt)
        assert ctx.loop_var == "I"
        assert ctx.loop_type == ForLoopType.STRING_LIST

    def test_for_gen_context_from_argumentless(self):
        """ForGenContext correctly analyzes argumentless FOR loop."""
        from m2py.asg.enums import ForLoopType
        from m2py.asg.statements import MForStatement
        from m2py.asg.elements import MScope
        from m2py.codegen.statements import ForGenContext

        # Create argumentless FOR: F (no parameters)
        stmt = MForStatement(
            loop_var="",
            parameters=[],
            body=MScope(statements=[]),
        )
        # Set loop_type (normally set by analyze_for_loops())
        stmt.loop_type = ForLoopType.ARGUMENTLESS

        ctx = ForGenContext.from_statement(stmt)
        assert ctx.loop_type == ForLoopType.ARGUMENTLESS
        assert ctx.is_infinite is True

    def test_for_gen_context_detects_modified_loop_var(self):
        """ForGenContext detects loop variable modification from analysis."""
        from m2py.asg.enums import ForLoopType, ForParamType
        from m2py.asg.statements import MForParameter, MForStatement
        from m2py.asg.elements import MScope
        from m2py.asg.expressions import MLiteral
        from m2py.codegen.statements import ForGenContext

        param = MForParameter(
            param_type=ForParamType.RANGE,
            start=MLiteral(value=1),
            step=MLiteral(value=1),
            end=MLiteral(value=10),
        )
        stmt = MForStatement(
            loop_var="I",
            parameters=[param],
            body=MScope(statements=[]),
        )
        # Set analysis flags (normally set by analysis passes)
        stmt.loop_type = ForLoopType.BOUNDED
        stmt.loop_var_modified_in_body = True

        ctx = ForGenContext.from_statement(stmt)
        assert ctx.use_while is True


@pytest.mark.codegen
class TestForIndirectionCodegen:
    """Tests for FOR with indirect loop variable (T068)."""

    def test_for_indirect_loop_var_bounded(self, execute_mumps):
        """FOR with indirect loop variable bounded range (T068).

        FOR @A=1:1:3 sets the variable whose name is in A.
        """
        result = execute_mumps('TEST\n S V="X" F @V=1:1:3 W X\n Q\n')
        assert result.output == "123"
        assert result.success is True

    def test_for_indirect_loop_var_string_list(self, execute_mumps):
        """FOR with indirect loop variable string list (T068).

        FOR @A="X","Y","Z" iterates through strings.
        """
        result = execute_mumps('TEST\n S V="I" F @V="A","B","C" W I\n Q\n')
        assert result.output == "ABC"
        assert result.success is True

    def test_for_indirect_loop_var_open_ended(self, execute_mumps):
        """FOR with indirect loop variable open-ended (T068).

        FOR @A=1:1 with QUIT in body.
        """
        result = execute_mumps('TEST\n S V="X" F @V=1:1 W X Q:X>3\n Q\n')
        assert result.output == "1234"
        assert result.success is True

    def test_for_indirect_loop_var_codegen(self, generate_python):
        """FOR with indirect loop variable generates correct code (T068)."""
        code = generate_python('TEST\n S V="X" F @V=1:1:3 W X\n Q\n')
        # Should resolve indirection before loop
        assert "_for_indirect_var" in code
        # Should use resolve_indirection_name for FOR loop indirection
        assert "resolve_indirection_name" in code

    def test_for_subscripted_loop_variable(self, execute_mumps):
        """FOR with subscripted loop variable (§8.2.5).

        T034: Subscripted FOR loop variables (F I(1)=1:1:3) should work correctly.
        The loop value is stored in the subscripted variable, not the root.
        """
        result = execute_mumps("TEST\n F I(1)=1:1:3 W I(1)\n Q\n")
        assert result.output == "123"
        assert result.success is True

    def test_for_subscripted_loop_variable_multiple_subs(self, execute_mumps):
        """FOR with multiple subscripts on loop variable (§8.2.5).

        T034: Multiple subscripts should also work.
        """
        result = execute_mumps("TEST\n F I(1,2)=1:1:3 W I(1,2)\n Q\n")
        assert result.output == "123"
        assert result.success is True

    def test_for_subscripted_loop_variable_codegen(self, generate_python):
        """FOR with subscripted loop variable generates .set() call (§8.2.5).

        T034: Subscripted loop var should use MArray.set() for initial and increment.
        """
        code = generate_python("TEST\n F I(1)=1:1:3 W I(1)\n Q\n")
        # Should use .set() for initial value assignment
        assert ".set(1, value=_for_start_0)" in code
        # Should use .set() for increment assignment
        assert ".set(1, value=_for_cur_0)" in code
