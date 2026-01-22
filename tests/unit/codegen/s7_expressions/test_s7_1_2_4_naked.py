"""Tests for naked global references code generation (§7.1.2.4).

Naked global references use the "naked indicator" which tracks the base
(global name and all-but-last subscript) from the most recent global access.
^(subscripts) resolves to the base plus the new subscripts.

Key behaviors (FR-046):
- Naked indicator is set by any full global reference
- Naked reference ^(sub) uses prior global's name
- Naked indicator is sequence-dependent (order matters)
- Invalid if no prior global reference exists

Reference: MUMPS 1995 ANSI Standard, Section 7.1.2.4
Parser/ASG tests are in tests/unit/asg/s7_expressions/test_s7_1_2_variables.py

Consolidated from:
- tests/unit/codegen/test_spec_009_naked.py (Spec 009 Phase 7 - User Story 5)
- tests/unit/cross_cutting/test_naked_references.py
"""

import pytest


# =============================================================================
# Basic Naked Global Reference Tests
# =============================================================================


@pytest.mark.codegen
class TestNakedGlobalBasic:
    """Tests for basic naked global reference operations.

    Acceptance Scenarios from Spec 009:
    1. S ^A(1,2)=1 S ^(3)=2 W ^A(1,3) → "2" (naked replaces last subscript)
    2. S ^B(1,2,3)=1 S ^(4)=2 W ^B(1,2,4) → "2" (works with deeper nesting)
    3. S ^C(1,2)=1 S ^(3,4)=2 W ^C(1,3,4) → "2" (multiple new subscripts)
    4. S ^D(1)=1 W ^(1) → "1" (naked read)
    5. S ^E(1,2)=1 S ^F(3,4)=2 S ^(5)=3 W ^F(3,5) → "3" (naked follows last global)
    """

    def test_naked_replaces_last_subscript(self, execute_mumps):
        """Scenario 1: Naked reference replaces last subscript.

        S ^A(1,2)=1 S ^(3)=2 W ^A(1,3) → "2"

        After ^A(1,2), naked indicator = ("A", ("1",))
        ^(3) resolves to ^A(1,3)
        """
        result = execute_mumps("TEST S ^A(1,2)=1 S ^(3)=2 W ^A(1,3) Q")
        assert result.output == "2"

    def test_naked_with_deeper_nesting(self, execute_mumps):
        """Scenario 2: Naked reference works with deeper nesting.

        S ^B(1,2,3)=1 S ^(4)=2 W ^B(1,2,4) → "2"

        After ^B(1,2,3), naked indicator = ("B", ("1", "2"))
        ^(4) resolves to ^B(1,2,4)
        """
        result = execute_mumps("TEST S ^B(1,2,3)=1 S ^(4)=2 W ^B(1,2,4) Q")
        assert result.output == "2"

    def test_naked_multiple_new_subscripts(self, execute_mumps):
        """Scenario 3: Naked reference with multiple new subscripts.

        S ^C(1,2)=1 S ^(3,4)=2 W ^C(1,3,4) → "2"

        After ^C(1,2), naked indicator = ("C", ("1",))
        ^(3,4) resolves to ^C(1,3,4)
        """
        result = execute_mumps("TEST S ^C(1,2)=1 S ^(3,4)=2 W ^C(1,3,4) Q")
        assert result.output == "2"

    def test_naked_read(self, execute_mumps):
        """Scenario 4: Naked reference for reading.

        S ^D(1)=1 W ^(1) → "1"

        After ^D(1), naked indicator = ("D", ())
        ^(1) resolves to ^D(1)
        """
        result = execute_mumps("TEST S ^D(1)=1 W ^(1) Q")
        assert result.output == "1"

    def test_naked_follows_last_global(self, execute_mumps):
        """Scenario 5: Naked follows most recently accessed global.

        S ^E(1,2)=1 S ^F(3,4)=2 S ^(5)=3 W ^F(3,5) → "3"

        ^E(1,2) sets indicator to ("E", ("1",))
        ^F(3,4)=2 sets indicator to ("F", ("3",))
        ^(5) resolves to ^F(3,5)
        """
        result = execute_mumps("TEST S ^E(1,2)=1 S ^F(3,4)=2 S ^(5)=3 W ^F(3,5) Q")
        assert result.output == "3"


# =============================================================================
# Naked Reference State Transition Tests
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
# Naked Reference Error Conditions
# =============================================================================


@pytest.mark.codegen
class TestNakedReferenceErrors:
    """Codegen tests for naked reference error conditions.

    Naked reference without prior global reference is an error (M1).
    Reference: §7.1.2.4, FR-046
    """

    def test_naked_without_prior_global_error(self, execute_mumps):
        """Naked reference without prior global raises error (§7.1.2.4).

        At start of routine or after indicator cleared, using ^(1) is an error.
        MUMPS standard requires M1 error; YDB raises GVNAKED error.
        """
        result = execute_mumps("TEST W ^(1),! Q")
        assert not result.success
        # Error should be raised - either NAKEDERR or GVNAKED
        error_text = (result.error or result.output).upper()
        assert "NAKED" in error_text

    def test_naked_indicator_scope(self, execute_mumps):
        """Naked indicator scope within routine execution (§7.1.2.4).

        The naked indicator persists across statements within same execution.

        YDB verified: S ^DATA(1)=1 S X=^(1) S ^(2)=X W ^DATA(2) → "1"
        """
        result = execute_mumps("TEST S ^DATA(1)=1 S X=^(1) S ^(2)=X W ^DATA(2) Q")
        assert result.output == "1"


# =============================================================================
# Naked Reference Edge Cases
# =============================================================================


@pytest.mark.codegen
class TestNakedGlobalEdgeCases:
    """Edge case tests for naked global references.

    Reference: §7.1.2.4, FR-046
    """

    def test_naked_after_root_global(self, execute_mumps):
        """Naked after global with no subscripts."""
        # After ^G=1, indicator becomes None (no subscripts means naked is undefined)
        # But ^G(1)=2 sets indicator to ("G", ())
        result = execute_mumps("TEST S ^G(1)=1 S ^G=2 S ^G(1)=3 W ^(1) Q")
        # After ^G(1)=3, indicator = ("G", ()), ^(1) = ^G(1)
        assert result.output == "3"

    def test_naked_chain(self, execute_mumps):
        """Multiple naked references in sequence."""
        result = execute_mumps("TEST S ^H(1,2)=1 S ^(3)=2 S ^(4)=3 W ^H(1,4) Q")
        # After ^H(1,2), indicator = ("H", ("1",))
        # After ^(3), we're setting ^H(1,3), indicator = ("H", ("1",))
        # After ^(4), we're setting ^H(1,4), indicator = ("H", ("1",))
        assert result.output == "3"

    def test_naked_read_undefined(self, execute_mumps):
        """Naked read of undefined location returns empty string."""
        result = execute_mumps("TEST S ^I(1)=1 W ^(99) Q")
        # ^(99) = ^I(99) which is undefined
        assert result.output == ""

    def test_naked_with_string_subscripts(self, execute_mumps):
        """Naked reference with string subscripts."""
        result = execute_mumps('TEST S ^J("a","b")=1 S ^("c")=2 W ^J("a","c") Q')
        # After ^J("a","b"), indicator = ("J", ("a",))
        # ^("c") = ^J("a","c")
        assert result.output == "2"

    def test_naked_updates_after_read(self, execute_mumps):
        """Naked indicator updates after read operations too."""
        result = execute_mumps(
            "TEST S ^K(1,2)=1 S ^K(3,4)=2 W ^K(1,2) S ^(3)=99 W ^K(1,3) Q"
        )
        # After S ^K(1,2), indicator = ("K", ("1",))
        # After S ^K(3,4), indicator = ("K", ("3",))
        # W ^K(1,2) updates indicator to ("K", ("1",))
        # S ^(3) = S ^K(1,3) = 99
        assert result.output == "199"

    def test_data_function_with_naked(self, execute_mumps):
        """$DATA(^(1)) uses naked reference at runtime (§7.1.2.4).

        ASG parsing is tested in test_s7_1_5_intrinsic_functions.py.
        This tests runtime resolution of the naked reference.

        YDB verified: S ^A(1)=1 W $D(^(1)),! → "1"
        """
        result = execute_mumps("TEST S ^A(1)=1 W $D(^(1)) Q")
        assert result.output == "1"

    def test_order_function_with_naked(self, execute_mumps):
        """$ORDER(^(sub)) uses naked reference at runtime (§7.1.2.4).

        ASG parsing is tested in test_s7_1_5_intrinsic_functions.py.
        This tests runtime resolution of the naked reference.

        YDB verified: S ^A(1)=1,^A(2)=2 W $O(^("")),! → "1"
        """
        result = execute_mumps('TEST S ^A(1)=1,^A(2)=2 W $O(^("")) Q')
        assert result.output == "1"

    def test_kill_with_naked(self, execute_mumps):
        """KILL ^(sub) uses naked reference at runtime (§7.1.2.4).

        ASG parsing is tested in test_s8_2_11_kill.py.
        This tests runtime resolution of the naked reference.

        YDB verified: S ^A(1)=1,^A(2)=2 K ^(1) W $D(^A(1)) → "0"
        """
        result = execute_mumps("TEST S ^A(1)=1,^A(2)=2 K ^(1) W $D(^A(1)) Q")
        assert result.output == "0"

    def test_merge_source_with_naked(self, execute_mumps):
        """MERGE ^DEST=^(src) uses naked reference as source (§7.1.2.4).

        MERGE supports naked reference as SOURCE. The naked indicator is set
        by the prior global access, and ^(src) resolves to that global.

        Note: MERGE with naked DESTINATION (M ^(dest)=^SRC) raises M1 error
        in YDB - naked references are not allowed as MERGE destinations.

        YDB verified: S ^A(1)=5 M ^B=^(1) W ^B → "5"
        """
        result = execute_mumps("TEST S ^A(1)=5 M ^B=^(1) W ^B Q")
        assert result.output == "5"

    @pytest.mark.stub
    def test_lock_with_naked(self, generate_python):
        """LOCK ^(sub) raises NotImplementedError (YDB restriction).

        Per YDB documentation, LOCK requires explicit global names.
        Error: %YDB-E-LKNAMEXPECTED, An identifier is expected after a ^

        Note: The MUMPS 1995 standard §8.2.12 does not explicitly forbid
        naked references in LOCK nrefs, but YDB rejects them. This is a
        YDB-specific restriction that m2py enforces at codegen time.
        """
        with pytest.raises(
            NotImplementedError, match="Naked reference not supported in LOCK"
        ):
            generate_python("TEST S ^A(1)=5 L ^(1) Q")
