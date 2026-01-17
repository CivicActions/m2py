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
