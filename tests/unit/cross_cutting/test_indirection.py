"""Cross-cutting tests for indirection RUNTIME behavior (Section 6.3.1, 7.3).

This file contains tests for cross-cutting indirection behavior that
test codegen/runtime behavior requiring execution.

From MUMPS 1995 ANSI Standard and spec reference 1995__a901027.md:

1. Name indirection: @VAR evaluates to a variable name
2. Argument indirection: @VAR evaluates to a command argument
3. Pattern indirection: X?@VAR where VAR contains a pattern
4. Subscript indirection (1984): @VAR@(subs)

Reference: MUMPS 1995 ANSI Standard
Spec 012: Phase 3 - User Story 1: Name Indirection
"""

import pytest


# =============================================================================
# Indirection Integration Tests - Generated code execution
# =============================================================================


@pytest.mark.codegen
class TestNameIndirectionExecution:
    """Integration tests for name indirection runtime behavior (T023).

    These tests execute generated Python code to verify that indirection
    works correctly at runtime.
    """

    def test_simple_name_indirection_set(self, execute_mumps):
        """S @X=1 where X="VAR" sets VAR to 1.

        Example: S X="VAR",@X=1 W VAR => outputs 1
        """
        result = execute_mumps('TEST S X="VAR",@X=1 W VAR Q\n')
        assert result.output == "1"

    def test_simple_name_indirection_read(self, execute_mumps):
        """@X where X="VAR" reads VAR's value.

        Example: S X="VAR",VAR=5,Y=@X W Y => outputs 5
        """
        result = execute_mumps('TEST S X="VAR",VAR=5,Y=@X W Y Q\n')
        assert result.output == "5"

    def test_double_level_indirection(self, execute_mumps):
        """@@X chains two levels of dereference.

        Example: S A="B",B="C",C=100,X=@@A W X => outputs 100
        Because @@A -> @B -> C -> 100
        """
        result = execute_mumps('TEST S A="B",B="C",C=100,X=@@A W X Q\n')
        assert result.output == "100"


@pytest.mark.codegen
class TestIndirectionCodegen:
    """Codegen tests for indirection runtime behavior.

    Generated Python code must correctly handle all indirection
    types at runtime.

    Reference: §6.3.1, §7.3
    """

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Codegen not yet implemented: argument indirection execution"
    )
    def test_argument_indirection_resolves_at_runtime(self):
        """Argument indirection resolves argument at runtime (§7.3.2).

        Per 1995__a901027.md: "Write @$Select(ENOUGH:SPACE,1:PAGE)"
        The argument to WRITE is determined by evaluating the indirection.
        """
        pytest.fail("Stub - implement when codegen supports indirection")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Codegen not yet implemented: pattern indirection execution"
    )
    def test_pattern_indirection_resolves_at_runtime(self):
        """Pattern indirection resolves pattern at runtime (§7.2.5.5).

        Per 1995__a901027.md: "Write string?@pattern" where pattern="3N1...4N"
        The pattern string is retrieved and compiled at runtime.
        """
        pytest.fail("Stub - implement when codegen supports indirection")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Pre-existing bug: subscripted SET doesn't initialize MArray"
    )
    def test_subscripted_indirection_resolves_correctly(self):
        """Subscripted indirection @VAR@(1,2) works correctly (§7.3.1).

        Per 1984 addition (1995__a901027.md):
        "@ARRAY@(1,2,3) where ARRAY='PRICES' refers to PRICES(1,2,3)"
        The base is resolved first, then subscripts are appended.

        Note: Blocked by pre-existing bug where subscripted SET
        (S ARRAY(1,2)=5) doesn't properly initialize MArray.
        """
        pytest.fail("Blocked by pre-existing subscripted SET bug")


# =============================================================================
# XECUTE Integration Tests - Generated code execution
# =============================================================================


@pytest.mark.codegen
class TestXecuteExecution:
    """Integration tests for XECUTE runtime behavior.

    Spec 012 Phase 4 (T031): Verify constant XECUTE produces readable
    inlined Python code and executes correctly.
    Spec 012 Phase 5 (T037): Verify dynamic XECUTE with scope access.
    """

    def test_xecute_constant_set_inlined(self, execute_mumps):
        """X "S X=1" sets X via inlined Python.

        The constant string should be parsed at transpile time
        and generate _scope['X'] = 1 inline.
        """
        result = execute_mumps('TEST X "S X=1" W X Q\n')
        assert result.output == "1"

    def test_xecute_multiple_constant_strings(self, execute_mumps):
        """X "S A=1","S B=2" processes each string in order.

        Both constant strings should be inlined, A then B.
        """
        result = execute_mumps('TEST X "S A=1","S B=2" W A,B Q\n')
        assert result.output == "12"

    def test_xecute_postcondition_true_executes(self, execute_mumps):
        """X:P=1 "S X=5" executes when postcondition is true.

        When P=1, the XECUTE should execute and set X=5.
        """
        result = execute_mumps('TEST S P=1 X:P=1 "S X=5" W X Q\n')
        assert result.output == "5"

    def test_xecute_postcondition_false_skips(self, execute_mumps):
        """X:P=1 "S X=5" skips when postcondition is false.

        When P=0, the XECUTE should NOT execute and X remains undefined.
        """
        # Note: Undefined variable returns empty string in m2py
        result = execute_mumps('TEST S P=0 X:P=1 "S X=5" W X Q\n')
        assert result.output == ""

    def test_xecute_constant_produces_readable_python(self):
        """Constant XECUTE generates readable inlined Python (T031).

        The generated code should contain direct variable assignments
        rather than runtime.execute() calls.
        """
        from m2py.codegen import generate_python

        code = generate_python('TEST X "S X=1" Q')

        # Should have inline assignment (MArray-based format)
        assert "_scope.setdefault('X', MArray()).value = 1" in code

        # Should NOT have runtime execute call
        assert "execute_mumps" not in code
        assert "_rt.execute" not in code

    # --- Phase 5: Dynamic XECUTE Integration Tests (T037) ---

    def test_xecute_dynamic_basic(self, execute_mumps):
        """S CODE="W 42" X CODE executes dynamic code (T037).

        Spec 012 Phase 5: Dynamic XECUTE parses and runs at runtime.
        """
        result = execute_mumps('TEST S CODE="W 42" X CODE Q\n')
        assert result.output == "42"

    def test_xecute_dynamic_scope_read(self, execute_mumps):
        """XECUTEd code can access outer scope variables (T037).

        S OUTER=10 X "S INNER=OUTER+1" W INNER → outputs 11
        """
        result = execute_mumps('TEST S OUTER=10 X "S INNER=OUTER+1" W INNER Q\n')
        assert result.output == "11"

    def test_xecute_dynamic_scope_modify(self, execute_mumps):
        """XECUTEd code can modify outer scope variables (T037).

        S OUTER=10 X "S OUTER=99" W OUTER → outputs 99
        """
        result = execute_mumps('TEST S OUTER=10 X "S OUTER=99" W OUTER Q\n')
        assert result.output == "99"

    def test_xecute_dynamic_concatenated_code(self, execute_mumps):
        """XECUTE works with runtime-constructed code strings (T037).

        S CODE="S X=" S CODE=CODE_"5" X CODE W X → outputs 5
        """
        result = execute_mumps('TEST S CODE="S X=" S CODE=CODE_"5" X CODE W X Q\n')
        assert result.output == "5"

    def test_xecute_dynamic_multiple_args(self, execute_mumps):
        """X A,B with dynamic args executes each in order (T037).

        S A="S X=1",B="S Y=2" X A,B W X,Y → outputs 12
        """
        result = execute_mumps('TEST S A="S X=1",B="S Y=2" X A,B W X,Y Q\n')
        assert result.output == "12"

    def test_xecute_dynamic_with_postcondition_true(self, execute_mumps):
        """Dynamic XECUTE respects postcondition when true (T037).

        S P=1,CODE="S X=5" X:P=1 CODE W X → outputs 5
        """
        result = execute_mumps('TEST S P=1,CODE="S X=5" X:P=1 CODE W X Q\n')
        assert result.output == "5"

    def test_xecute_dynamic_with_postcondition_false(self, execute_mumps):
        """Dynamic XECUTE respects postcondition when false (T037).

        S P=0,CODE="S X=5" X:P=1 CODE W X → outputs empty (X undefined)
        """
        result = execute_mumps('TEST S P=0,CODE="S X=5" X:P=1 CODE W X Q\n')
        assert result.output == ""

    def test_xecute_dynamic_produces_runtime_call(self):
        """Dynamic XECUTE generates execute_mumps call (T037).

        The generated code should call _rt.execute_mumps() at runtime.
        """
        from m2py.codegen import generate_python

        code = generate_python('TEST S CODE="S X=1" X CODE Q')

        # Should have runtime execute_mumps call
        assert "execute_mumps" in code
        # Should pass _scope for shared variable access
        assert "_scope)" in code

    # --- Phase 6: XECUTE $TEST Semantics Integration Tests (T041) ---

    def test_xecute_constant_test_mutation_visible(self, execute_mumps):
        """I 1=1 X "I 0=1" E W "ELSE" → ELSE executes (T041).

        Spec 012 Phase 6: XECUTE does NOT stack $TEST.
        Inner IF sets $TEST=0, ELSE clause sees modified value.
        """
        result = execute_mumps('TEST I 1=1 X "I 0=1" E  W "ELSE" Q\n')
        assert result.output == "ELSE"

    def test_xecute_dynamic_test_mutation_visible(self, execute_mumps):
        """S CODE="I 0=1" I 1=1 X CODE E W "ELSE" → ELSE executes (T041).

        Dynamic XECUTE with IF modifies caller's $TEST.
        """
        result = execute_mumps('TEST S CODE="I 0=1" I 1=1 X CODE E  W "ELSE" Q\n')
        assert result.output == "ELSE"

    def test_xecute_dynamic_test_mutation_inverse(self, execute_mumps):
        """S CODE="I 1=1" I 0=1 X CODE E W "ELSE" → no output (T041).

        Outer IF sets $TEST=0, inner sets $TEST=1.
        ELSE doesn't execute because final $TEST=1.
        """
        result = execute_mumps('TEST S CODE="I 1=1" I 0=1 X CODE E  W "ELSE" Q\n')
        # ELSE should NOT execute - $TEST=1 after inner IF
        assert result.output == ""


# =============================================================================
# Indirect DO Integration Tests (Spec 012 Phase 7, T048)
# =============================================================================


@pytest.mark.codegen
class TestIndirectDoExecution:
    """Integration tests for indirect DO runtime behavior (T048).

    Spec 012 Phase 7: Support D @CMD for dynamic subroutine dispatch.
    These tests execute generated Python code to verify indirect DO
    works correctly at runtime.
    """

    def test_indirect_do_simple(self, execute_mumps):
        """S CMD="LABEL" D @CMD calls LABEL (T048).

        Spec 012 Phase 7 acceptance scenario:
        Given: S CMD="SUB" D @CMD
        When: executed
        Then: SUB is called and its output appears
        """
        result = execute_mumps('TEST S CMD="SUB" D @CMD Q\nSUB W "SubOut" Q\n')
        assert result.output == "SubOut"

    def test_indirect_do_with_explicit_offset(self, execute_mumps):
        """D @CMD+1 enters at offset from resolved label (T048).

        Given: S CMD="SUB" D @CMD+1
        When: executed
        Then: Enters SUB at line +1, skipping first line
        """
        result = execute_mumps(
            'TEST S CMD="SUB" D @CMD+1 Q\nSUB W "Skip"\n W "Show" Q\n'
        )
        assert result.output == "Show"

    def test_indirect_do_chained_calls(self, execute_mumps):
        """Multiple indirect DOs in sequence (T048).

        Given: S A="S1",B="S2" D @A,@B
        When: executed
        Then: Both S1 and S2 are called in order
        """
        result = execute_mumps(
            'TEST S A="S1",B="S2" D @A,@B Q\nS1 W "1" Q\nS2 W "2" Q\n'
        )
        assert result.output == "12"

    def test_indirect_do_computed_target(self, execute_mumps):
        """D @(computed expression) resolves at runtime (T048).

        Given: S X="SU",Y="B" D @(X_Y)
        When: executed
        Then: Concatenates X_Y to "SUB" and calls it
        """
        result = execute_mumps('TEST S X="SU",Y="B" D @(X_Y) Q\nSUB W "Concat" Q\n')
        assert result.output == "Concat"

    def test_indirect_do_return_to_caller(self, execute_mumps):
        """Indirect DO returns control to caller (T048).

        Given: D @CMD W "After"
        When: executed
        Then: Subroutine runs, returns, "After" is written
        """
        result = execute_mumps(
            'TEST S CMD="SUB" D @CMD W "After" Q\nSUB W "Before" Q\n'
        )
        assert result.output == "BeforeAfter"


# =============================================================================
# Indirect GOTO Integration Tests (Spec 012 Phase 8, T054)
# =============================================================================


@pytest.mark.codegen
class TestIndirectGotoExecution:
    """Integration tests for indirect GOTO runtime behavior (T054).

    Spec 012 Phase 8: Support G @TARGET for dynamic control flow.
    These tests execute generated Python code to verify indirect GOTO
    works correctly at runtime.
    """

    def test_indirect_goto_simple(self, execute_mumps):
        """S TARGET="DONE" G @TARGET transfers to DONE (T054).

        Spec 012 Phase 8 acceptance scenario:
        Given: S TARGET="DONE" G @TARGET
        When: executed
        Then: Control transfers to DONE, "Skip" is NOT written
        """
        result = execute_mumps(
            'TEST S TARGET="DONE" G @TARGET W "Skip" Q\nDONE W "Done" Q\n'
        )
        assert result.output == "Done"

    def test_indirect_goto_with_explicit_offset(self, execute_mumps):
        """G @TARGET+1 enters at offset from resolved label (T054).

        Given: S TARGET="DONE" G @TARGET+1
        When: executed
        Then: Enters DONE at line +1, skipping first line
        """
        result = execute_mumps(
            'TEST S TARGET="DONE" G @TARGET+1 Q\nDONE W "Skip"\n W "Show" Q\n'
        )
        assert result.output == "Show"

    def test_indirect_goto_skips_intervening_code(self, execute_mumps):
        """G @TARGET skips all code between GOTO and target (T054).

        Given: W "A" G @TARGET W "B" W "C"
        When: executed
        Then: Only "A" and "D" are written (B and C skipped)
        """
        result = execute_mumps(
            'TEST W "A" S TARGET="DONE" G @TARGET W "B" W "C" Q\nDONE W "D" Q\n'
        )
        assert result.output == "AD"

    def test_indirect_goto_computed_target(self, execute_mumps):
        """G @(computed expression) resolves at runtime (T054).

        Given: S X="DO",Y="NE" G @(X_Y)
        When: executed
        Then: Concatenates X_Y to "DONE" and jumps there
        """
        result = execute_mumps(
            'TEST S X="DO",Y="NE" G @(X_Y) W "Skip" Q\nDONE W "Concat" Q\n'
        )
        assert result.output == "Concat"

    def test_indirect_goto_does_not_return(self, execute_mumps):
        """G @TARGET does NOT return to caller (unlike DO) (T054).

        Given: W "Before" G @TARGET W "After"
        When: executed
        Then: Only "Before" and "Target" written, "After" is NOT
        """
        result = execute_mumps(
            'TEST W "Before" S TARGET="DONE" G @TARGET W "After" Q\nDONE W "Target" Q\n'
        )
        # GOTO does not return, so "After" is never executed
        assert result.output == "BeforeTarget"


# =============================================================================
# Argument Indirection Integration Tests (Spec 012 Phase 9, T059)
# =============================================================================


@pytest.mark.codegen
class TestArgumentIndirectionExecution:
    """Integration tests for SET argument indirection runtime behavior (T059).

    Spec 012 Phase 9: Support S @A where A contains "X=1,Y=2".
    These tests execute generated Python code to verify argument
    indirection works correctly at runtime.
    """

    def test_argument_indirection_multiple_vars(self, execute_mumps):
        """S A="X=1",B="Y=2" S @A,@B sets both X and Y (T059).

        Spec 012 Phase 9 acceptance scenario:
        Given: S A="X=1",B="Y=2" S @A,@B
        When: executed
        Then: X=1 and Y=2
        """
        result = execute_mumps('TEST S A="X=1",B="Y=2" S @A,@B W X,Y Q\n')
        assert result.output == "12"

    def test_argument_indirection_string_with_multiple_assigns(self, execute_mumps):
        """S A="X=1,Y=2" S @A processes entire string as SET args (T059).

        Given: S A="X=1,Y=2" S @A
        When: executed
        Then: Both X=1 and Y=2 are set from single indirection
        """
        result = execute_mumps('TEST S A="X=1,Y=2" S @A W X,Y Q\n')
        assert result.output == "12"

    def test_argument_indirection_order_preserved(self, execute_mumps):
        """S Z=9,@A,@B,W=4 processes all in left-to-right order (T059).

        Given: S A="X=1",B="Y=2" S Z=9,@A,@B,W=4
        When: executed
        Then: Z=9, X=1, Y=2, W=4 in that order
        """
        result = execute_mumps('TEST S A="X=1",B="Y=2" S Z=9,@A,@B,W=4 W Z,X,Y,W Q\n')
        assert result.output == "9124"
