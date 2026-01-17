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
