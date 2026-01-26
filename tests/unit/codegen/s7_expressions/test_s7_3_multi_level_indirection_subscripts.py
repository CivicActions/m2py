"""Tests for multi-level indirection with per-level subscripts.

These tests verify that @@X@(1,2)@(5,6) properly handles subscripts
at multiple indirection levels.
"""

import pytest


@pytest.mark.codegen
class TestMultiLevelIndirectionWithSubscripts:
    """Tests for multi-level indirection with subscripts at multiple levels."""

    def test_double_indirection_with_per_level_subscripts_local(self, execute_mumps):
        """Test @@X@(1,2)@(5,6) with local variables."""
        code = """TEST
 S X="A",A(1,2)="B(3,4)",@@X@(1,2)@(5,6)=1
 W B(3,4,5,6)
 Q
"""
        result = execute_mumps(code)
        assert result.output == "1", f"Expected '1', got {result.output!r}"

    def test_double_indirection_with_complex_inner_subscripts(self, execute_mumps):
        """Test @@X@(1,2)@(expr,6) with expression in subscript."""
        code = """TEST
 S X="A",A(1,2)="B(1,2)",B(1,2)=5,@@X@(1,2)@(@A(1,2),6)=2
 W B(1,2,5,6)
 Q
"""
        result = execute_mumps(code)
        assert result.output == "2", f"Expected '2', got {result.output!r}"

    def test_double_indirection_with_nested_indirection_subscript(self, execute_mumps):
        """Test @@X@(1,2)@(@@X@(1,2)@(5,6)+4,7) where subscript contains indirection."""
        code = """TEST
 S X="A",A(1,2)="B(1,2)",B(1,2,5,6)=2
 S @@X@(1,2)@(@@X@(1,2)@(5,6)+4,7)=3
 W B(1,2,6,7)
 Q
"""
        result = execute_mumps(code)
        assert result.output == "3", f"Expected '3', got {result.output!r}"

    def test_double_indirection_with_per_level_subscripts_global(self, execute_mumps):
        """Test @@^V2@(1,2)@(5,6) with global variables."""
        code = """TEST
 K ^VV,^V,^V2
 S ^V2="^VV",^VV(1,2)="^VV(3,4)",@@^V2@(1,2)@(5,6)=1
 W ^VV(3,4,5,6)
 Q
"""
        result = execute_mumps(code)
        assert result.output == "1", f"Expected '1', got {result.output!r}"

    def test_double_indirection_read_with_per_level_subscripts(self, execute_mumps):
        """Test reading via @@X@(1,2)@(5,6) expression."""
        code = """TEST
 S X="A",A(1,2)="B(1,2)",B(1,2,5,6)=42
 W @@X@(1,2)@(5,6)
 Q
"""
        result = execute_mumps(code)
        assert result.output == "42", f"Expected '42', got {result.output!r}"

    def test_double_indirection_read_global_per_level(self, execute_mumps):
        """Test reading via @@^V@(1,2)@(5,6) with global variables."""
        code = """TEST
 K ^VV,^V
 S ^V="^VV",^VV(1,2)="^V(1,2)",^V(1,2,5,6)=99
 W @@^V@(1,2)@(5,6)
 Q
"""
        result = execute_mumps(code)
        assert result.output == "99", f"Expected '99', got {result.output!r}"


@pytest.mark.codegen
class TestSubscriptedVariableInIndirection:
    """Tests for @A(1,2) where the inner variable has subscripts."""

    def test_simple_subscripted_indirection_source(self, execute_mumps):
        """Test @A(1,2) where A(1,2) contains variable name."""
        code = """TEST
 S A(1,2)="B(1,2)",B(1,2)=5
 W @A(1,2)
 Q
"""
        result = execute_mumps(code)
        assert result.output == "5", f"Expected '5', got {result.output!r}"

    def test_subscripted_indirection_source_in_subscript(self, execute_mumps):
        """Test @A(1,2) used as subscript expression."""
        code = """TEST
 S A(1,2)="B(1,2)",B(1,2)=3
 S C(@A(1,2))=7
 W C(3)
 Q
"""
        result = execute_mumps(code)
        assert result.output == "7", f"Expected '7', got {result.output!r}"


@pytest.mark.codegen
class TestVV2VNIATestCases:
    """Specific test cases from the VV2VNIA test suite for II-127, II-128, and II-129."""

    def test_ii127_multi_use_local_name_indirection(self, execute_mumps):
        """Test II-127: Multi use variable name indirection with locals."""
        code = """TEST
 S VCOMP=""
 S X="A",A(1,2)="B(3,4)",@@X@(1,2)@(5,6)=1
 S X="A",A(1,2)="B(1,2)",B(1,2)=5,@@X@(1,2)@(@A(1,2),6)=2
 S @@X@(1,2)@(@@X@(1,2)@(5,6)+4,7)=3
 S VCOMP=VCOMP_B(3,4,5,6)_B(1,2,5,6)_B(1,2,6,7)
 W VCOMP
 Q
"""
        result = execute_mumps(code)
        assert result.output == "123", f"Expected '123', got {result.output!r}"

    def test_ii128_multi_use_global_name_indirection(self, execute_mumps):
        """Test II-128: Multi use variable name indirection with globals."""
        code = """TEST
 K ^VV,^V,^V2
 S VCOMP=""
 S ^V2="^VV",^VV(1,2)="^VV(3,4)",@@^V2@(1,2)@(5,6)=1
 S ^VV(1,2)="^V(1,2)",^V(1,2)=5,@@^V2@(1,2)@(@^VV(1,2),6)=2
 S @@^V2@(1,2)@(@@^V2@(1,2)@(5,6)+4,7)=3
 S VCOMP=VCOMP_^VV(3,4,5,6)_^V(1,2,5,6)_^V(1,2,6,7)
 W VCOMP
 Q
"""
        result = execute_mumps(code)
        assert result.output == "123", f"Expected '123', got {result.output!r}"

    def test_ii129_naked_indicator_in_name_indirection(self, execute_mumps):
        """Test II-129: Naked indicator effect in variable name indirection.

        This test verifies that when indirection yields a naked reference string
        like "^(5)", it is properly resolved using the current naked indicator.
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
 ; @@^(1)@(^(2)) resolves:
 ;   @^(1) = @"^(5)" where "^(5)" is a naked ref string = ^V(5)
 ;   @(^(2)) = @(1)
 ;   So @"^(5)"@(1) = ^V(5,1) = "^(3)"
 ;   Then @"^(3)" = ^V(5,3) (naked is ("V", ("5",)) after reading ^V(5,1))
 S @@^(1)@(^(2))=3
 S VCOMP=VCOMP_^(3)_^V(5,3)
 W VCOMP
 Q
"""
        result = execute_mumps(code)
        assert result.output == "22033", f"Expected '22033', got {result.output!r}"


@pytest.mark.codegen
class TestNakedReferenceInIndirection:
    """Tests for naked references within indirection contexts."""

    def test_naked_reference_string_resolved_in_indirection(self, execute_mumps):
        """Test that a naked reference string like "^(5)" is resolved in indirection.

        When indirection yields "^(5)", we need to resolve this as a naked reference
        using the current naked indicator, not try to get the value of a literal "^(5)".
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
        # @@^V(1) = @(value of @^V(1)) = @(value of "^V(1)") = @"^(3)" = ^V(3) = 42
        # Actually: @^V(1) = "^(3)", then @"^(3)" = ^V(3) = 42
        assert result.output == "42", f"Expected '42', got {result.output!r}"

    @pytest.mark.xfail(
        reason="Naked reference string in indirection result - edge case"
    )
    def test_naked_reference_with_subscripts_in_indirection(self, execute_mumps):
        """Test naked reference with subscripts in indirection context."""
        code = """TEST
 K ^V
 S ^V(1)="^(5)"
 ; naked = ("V", ())
 S ^V(5,1)=99
 ; naked = ("V", ("5",))
 ; Now we need to access @^V(1)@(1)
 ; @^V(1) = "^(5)" (a naked ref string)
 ; Resolve "^(5)" with current naked ("V", ()) NOT ("V", ("5",))
 ; But after reading ^V(1), naked is ("V", ())
 ; So "^(5)" → ^V(5), with subscript (1) → ^V(5,1) = 99
 W @^V(1)@(1)
 Q
"""
        result = execute_mumps(code)
        assert result.output == "99", f"Expected '99', got {result.output!r}"

    def test_ii124_gnamind_is_indirection(self, execute_mumps):
        """Test II-124: gnamind is indirection - @@^VV@(3)=3.

        This tests that regular global indirection (not naked) still works.
        """
        code = """TEST
 S ^VV="^VV(1)",^VV(1)="^VV(2)",^VV(2)="^VV(3)",^VV(3)="^VV(A,B)"
 S ^VV(1,3)="^VV(2,3)"
 S @@^VV@(3)=3
 W ^VV(2,3)
 Q
"""
        result = execute_mumps(code)
        assert result.output == "3", f"Expected '3', got {result.output!r}"
