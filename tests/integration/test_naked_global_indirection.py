"""Integration tests for Phase 8 User Story 6: Naked Global Indicator.

T076-T077: Tests that the naked indicator (`^(subs)`) works correctly
including through indirection.

Feature: 018-unified-variable-system, Phase 8 User Story 6
Requirements: FR-027 through FR-030 (Naked Global Indicator)

This verifies that:
1. Global access via indirection updates the naked indicator
2. Naked references after indirected global access resolve correctly
3. The II-129 torture test pattern works end-to-end
"""

import pytest

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


@pytest.fixture
def execute_mumps():
    """Fixture for parsing, generating, and executing MUMPS code."""

    def _execute(source: str, *, capture_output: bool = True):
        """Execute MUMPS source and return output string."""
        python_code = generate_python(source)
        runtime = MUMPSRuntime()
        result = runtime.execute(python_code, capture_output=capture_output)
        if result.error:
            return f"ERROR: {result.error}"
        return result.output

    return _execute


# =============================================================================
# T076: Torture Test II-129 - Naked Indicator After Indirection
# =============================================================================


@pytest.mark.integration
class TestII129NakedIndicatorAfterIndirection:
    """Torture test II-129: naked indicator after `@A@(subs)` indirection.

    This is the critical MUGJ VV2VNIA test that verifies naked indicator
    behavior with complex indirection patterns.
    """

    def test_ii129_independent_test(self, execute_mumps):
        """Independent test from tasks.md: `S A="^V(1)",@A@(1,2)=2 W ^(2)` outputs `2`.

        After @A@(1,2)=2:
        - @A resolves to "^V(1)"
        - @"^V(1)"@(1,2) = ^V(1,1,2) = 2
        - Naked indicator becomes ("V", ("1", "1"))
        - ^(2) resolves to ^V(1,1,2) = 2
        """
        result = execute_mumps('TEST K ^V S A="^V(1)",@A@(1,2)=2 W ^(2) Q')
        assert result == "2"

    def test_ii129_full_mugj_pattern(self, execute_mumps):
        """Full II-129 test from MUGJ VV2VNIA.m.

        Tests complex naked indicator updates through multiple indirection levels
        and verifies all intermediate values.
        """
        code = """TEST
 K ^V
 S A="^V(1)",@A@(1,2)=2
 ; After @A@(1,2)=2, naked = ("V", ("1", "1"))
 S VCOMP=^(2)_^V(1,1,2)
 ; ^(2) resolves to ^V(1,1,2) = 2
 S ^V(1)="^(5)",^(2)=1,^(5,1)="^(3)"
 ; naked = ("V", ("5",)) after ^(5,1)
 S VCOMP=VCOMP_$D(^V(11))
 ; $D(^V(11)) updates naked to ("V", ())
 ; Now ^(1) = ^V(1) = "^(5)", ^(2) = ^V(2) = 1
 S @@^(1)@(^(2))=3
 S VCOMP=VCOMP_^(3)_^V(5,3)
 W VCOMP
 Q
"""
        result = execute_mumps(code)
        assert result == "22033"


# =============================================================================
# T077: Global Access via Indirection Updates Naked Indicator
# =============================================================================


@pytest.mark.integration
class TestGlobalAccessViaIndirectionUpdatesNaked:
    """Test that global access via indirection updates the naked indicator."""

    def test_simple_global_indirection_updates_naked(self, execute_mumps):
        """S @A=5 where A="^G(1,2)" updates naked to ("G", ("1",)).

        After @A=5 sets ^G(1,2)=5, the naked indicator should be ("G", ("1",)).
        So ^(3) should resolve to ^G(1,3).
        """
        result = execute_mumps('TEST K ^G S A="^G(1,2)",@A=5,^(3)=7 W ^G(1,3) Q')
        assert result == "7"

    def test_multi_level_indirection_updates_naked(self, execute_mumps):
        """@@X where X="Y",Y="^G(1,2)" updates naked after resolving to ^G(1,2).

        The naked indicator should be updated based on the FINAL resolved global,
        not intermediate steps.
        """
        result = execute_mumps('TEST K ^G S X="Y",Y="^G(1,2)",@@X=5,^(3)=8 W ^G(1,3) Q')
        assert result == "8"

    def test_indirection_with_subscripts_updates_naked(self, execute_mumps):
        """@A@(1,2) where A="^G" updates naked to ("G", ("1",)).

        Per-level subscripts are applied, and the naked indicator reflects
        the full subscripted access.
        """
        result = execute_mumps('TEST K ^G S A="^G",@A@(1,2)=5,^(3)=9 W ^G(1,3) Q')
        assert result == "9"

    def test_naked_reference_string_in_indirection(self, execute_mumps):
        """Indirection resolving to "^(subs)" naked reference string.

        When indirection yields a naked reference string like "^(5)",
        it should be resolved using the current naked indicator.
        """
        code = """TEST
 K ^V
 S ^V(1)="^(3)"
 S ^V(3)=42
 ; ^V(1) contains "^(3)" which is a naked reference string
 ; After accessing ^V(1), naked = ("V", ())
 ; So "^(3)" should resolve to ^V(3) = 42
 W @@^V(1)
 Q
"""
        result = execute_mumps(code)
        assert result == "42"


# =============================================================================
# Additional Edge Cases for Naked Indicator with Indirection
# =============================================================================


@pytest.mark.integration
class TestNakedIndicatorEdgeCases:
    """Additional edge cases for naked indicator with indirection."""

    def test_read_via_indirection_updates_naked(self, execute_mumps):
        """W @A where A="^G(1,2)" also updates naked indicator.

        Even read access through indirection should update the naked indicator.
        """
        result = execute_mumps(
            'TEST K ^G S ^G(1,2)=5,A="^G(1,2)" S X=@A,^(3)=9 W ^G(1,3) Q'
        )
        assert result == "9"

    def test_nested_naked_in_indirection(self, execute_mumps):
        """Test nested naked reference resolution in indirection.

        ^(1) as indirection source, yielding another naked reference.
        """
        code = """TEST
 K ^V
 S ^V(1)="^(5)"
 ; naked = ("V", ())
 S ^V(5,1)=99
 ; naked = ("V", ("5",))
 ; Now @^V(1)@(1):
 ; @^V(1) = "^(5)" -> after reading ^V(1), naked = ("V", ())
 ; "^(5)" resolved as ^V(5)
 ; with subscript (1) -> ^V(5,1) = 99
 W @^V(1)@(1)
 Q
"""
        result = execute_mumps(code)
        assert result == "99"

    def test_kill_via_indirection_updates_naked(self, execute_mumps):
        """K @A where A="^G(1,2)" also updates naked indicator.

        KILL through indirection should update the naked indicator too.
        """
        code = """TEST
 K ^G
 S ^G(1,2)=5,^G(1,3)=7,A="^G(1,2)"
 K @A
 ; After K @A (which kills ^G(1,2)), naked = ("G", ("1",))
 W ^(3)
 Q
"""
        result = execute_mumps(code)
        assert result == "7"

    def test_data_via_indirection_updates_naked(self, execute_mumps):
        """$D(@A) where A="^G(1,2)" also updates naked indicator.

        $DATA through indirection should update the naked indicator.
        """
        code = """TEST
 K ^G
 S ^G(1,2)=5,^G(1,3)=7,A="^G(1,2)"
 S X=$D(@A),^(3)=9
 W ^G(1,3)
 Q
"""
        result = execute_mumps(code)
        assert result == "9"
