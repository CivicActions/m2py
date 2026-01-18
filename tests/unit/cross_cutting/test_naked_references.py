"""Cross-cutting tests for naked global references RUNTIME behavior (§7.1.2.4).

Naked references are a language feature that affects all global variable
access. A naked reference uses ^(subscripts) where the global name is
omitted and taken from the most recent global reference.

Key behaviors (FR-046):
- Naked indicator is set by any full global reference
- Naked reference ^(sub) uses prior global's name
- Naked indicator is sequence-dependent (order matters)
- Invalid if no prior global reference exists

Parser/ASG tests are in tests/unit/asg/s7_expressions/test_s7_1_2_variables.py

Reference: MUMPS 1995 ANSI Standard, Section 7.1.2.4
See also: FR-005 (cross-cutting features need dedicated tests)
         FR-046 (naked reference state tracking)
"""

import pytest


# =============================================================================
# Naked Reference State Transition Tests (Codegen Level)
# =============================================================================


@pytest.mark.codegen
class TestNakedStateTransitions:
    """Codegen tests for naked indicator state transitions.

    These tests verify RUNTIME behavior of naked reference resolution.
    The naked indicator must be tracked at runtime to resolve ^(sub) references.
    Reference: §7.1.2.4, FR-046
    """

    def test_set_establishes_naked_indicator(self, execute_mumps):
        """SET ^DATA(1)=X establishes naked indicator to ^DATA (§7.1.2.4).

        SET ^DATA(1)=X
        SET ^(2)=Y  ; Should access ^DATA(2) at runtime

        YDB verified: S ^DATA(1)=1 S ^(2)=2 W ^DATA(2) → "2"
        """
        result = execute_mumps("TEST S ^DATA(1)=1 S ^(2)=2 W ^DATA(2) Q")
        assert result.output == "2"

    def test_read_establishes_naked_indicator(self, execute_mumps):
        """SET X=^DATA(1) establishes naked indicator to ^DATA (§7.1.2.4).

        SET X=^DATA(1)  ; establishes indicator
        SET Y=^(2)      ; Should access ^DATA(2) at runtime

        YDB verified: S ^DATA(1)=1 S X=^(1) W X → "1"
        """
        result = execute_mumps("TEST S ^DATA(1)=1 S X=^(1) W X Q")
        assert result.output == "1"

    def test_naked_reference_subscript_chaining(self, execute_mumps):
        """Naked reference replaces last subscript, chains others (§7.1.2.4).

        SET ^DATA(1,2)=X  ; Indicator = ^DATA(1
        SET ^(3)=Y        ; Should access ^DATA(1,3) at runtime

        YDB verified: S ^DATA(1,2)=5 S ^(3)=7 W ^DATA(1,3) → "7"
        """
        result = execute_mumps("TEST S ^DATA(1,2)=5 S ^(3)=7 W ^DATA(1,3) Q")
        assert result.output == "7"

    def test_naked_reference_multiple_subscripts(self, execute_mumps):
        """Naked with multiple subscripts extends from indicator (§7.1.2.4).

        SET ^DATA(1)=X   ; Indicator = ^DATA
        SET ^(2,3)=Y     ; Should access ^DATA(2,3) at runtime

        YDB verified: S ^DATA(1)=1 S ^(2,3)=5 W ^DATA(2,3) → "5"
        """
        result = execute_mumps("TEST S ^DATA(1)=1 S ^(2,3)=5 W ^DATA(2,3) Q")
        assert result.output == "5"

    def test_naked_reference_updates_indicator(self, execute_mumps):
        """Naked reference itself updates the indicator (§7.1.2.4).

        SET ^DATA(1)=X   ; Indicator = ^DATA
        SET ^(2)=Y       ; Access ^DATA(2), indicator = ^DATA(
        SET ^(3)=Z       ; Should access ^DATA(3) at runtime

        YDB verified: S ^DATA(1)=1 S ^(2)=2 S ^(3)=3 W ^DATA(3) → "3"
        """
        result = execute_mumps("TEST S ^DATA(1)=1 S ^(2)=2 S ^(3)=3 W ^DATA(3) Q")
        assert result.output == "3"

    def test_different_global_changes_indicator(self, execute_mumps):
        """Reference to different global changes indicator (§7.1.2.4).

        SET ^DATA(1)=X    ; Indicator = ^DATA
        SET ^OTHER(5)=Y   ; Indicator = ^OTHER
        SET ^(6)=Z        ; Should access ^OTHER(6), not ^DATA(6)

        YDB verified: S ^DATA(1)=1 S ^OTHER(5)=2 S ^(6)=3 W ^OTHER(6) → "3"
        """
        result = execute_mumps("TEST S ^DATA(1)=1 S ^OTHER(5)=2 S ^(6)=3 W ^OTHER(6) Q")
        assert result.output == "3"


# =============================================================================
# Naked Reference Error Conditions (Codegen Level)
# =============================================================================


@pytest.mark.codegen
class TestNakedReferenceErrors:
    """Codegen tests for naked reference error conditions.

    Naked reference without prior global reference is an error (M1).
    Reference: §7.1.2.4, FR-046
    """

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: M1 error detection requires codegen"
    )
    def test_naked_without_prior_global_error(self):
        """Naked reference without prior global raises M1 error (§7.1.2.4).

        At start of routine or after indicator cleared, using ^(1) is an error.
        This test requires runtime execution to verify error M1 is raised.
        """
        pytest.fail("Stub - requires codegen runtime execution for M1 error")

    def test_naked_indicator_scope(self, execute_mumps):
        """Naked indicator scope within routine execution (§7.1.2.4).

        The naked indicator persists across statements within same execution.

        YDB verified: S ^DATA(1)=1 S X=^(1) S ^(2)=X W ^DATA(2) → "1"
        """
        result = execute_mumps("TEST S ^DATA(1)=1 S X=^(1) S ^(2)=X W ^DATA(2) Q")
        assert result.output == "1"


# =============================================================================
# Naked Reference Edge Cases (Codegen Level)
# =============================================================================


@pytest.mark.codegen
class TestNakedReferenceEdgeCases:
    """Codegen tests for naked reference edge cases.

    These tests verify RUNTIME behavior of naked references in various contexts.
    ASG parsing tests for these are in the respective command test files.
    Reference: §7.1.2.4, FR-046
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $DATA with naked at runtime")
    def test_data_function_with_naked(self):
        """$DATA(^(1)) uses naked reference at runtime (§7.1.2.4).

        ASG parsing is tested in test_s7_1_5_intrinsic_functions.py.
        This tests runtime resolution of the naked reference.
        """
        pytest.fail("Stub - requires codegen runtime execution")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $ORDER with naked at runtime")
    def test_order_function_with_naked(self):
        """$ORDER(^(sub)) uses naked reference at runtime (§7.1.2.4).

        ASG parsing is tested in test_s7_1_5_intrinsic_functions.py.
        This tests runtime resolution of the naked reference.
        """
        pytest.fail("Stub - requires codegen runtime execution")

    def test_kill_with_naked(self, execute_mumps):
        """KILL ^(sub) uses naked reference at runtime (§7.1.2.4).

        ASG parsing is tested in test_s8_2_11_kill.py.
        This tests runtime resolution of the naked reference.

        YDB verified: S ^A(1)=1,^A(2)=2 K ^(1) W $D(^A(1)) → "0"
        """
        result = execute_mumps("TEST S ^A(1)=1,^A(2)=2 K ^(1) W $D(^A(1)) Q")
        assert result.output == "0"

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: MERGE with naked at runtime")
    def test_merge_with_naked(self):
        """MERGE ^(dest)=^SRC uses naked at runtime (§7.1.2.4).

        ASG parsing is tested in test_s8_2_13_merge.py.
        This tests runtime resolution of the naked reference.
        """
        pytest.fail("Stub - requires codegen runtime execution")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: LOCK with naked at runtime")
    def test_lock_with_naked(self):
        """LOCK ^(sub) uses naked reference at runtime (§7.1.2.4).

        ASG parsing is tested in test_s8_2_12_lock.py.
        This tests runtime resolution of the naked reference.
        """
        pytest.fail("Stub - requires codegen runtime execution")
