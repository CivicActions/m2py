"""Tests for $TEXT with expression offsets (Spec 017 Phase 6).

Tests the fix for $TEXT offset expression type conversion:
- Non-literal offset expressions need int(m_num(...)) wrapping
- $TEXT with indirected labels: $T(@X) and $T(@X+N)

Reference: MUMPS 1995 ANSI Standard, Section 7.1.5 ($TEXT)
VV2VNIC MVTS tests
"""

import pytest


# =============================================================================
# $TEXT with Expression Offsets (Type Conversion)
# =============================================================================


@pytest.mark.codegen
@pytest.mark.spec017
class TestTextExpressionOffset:
    """Tests for $TEXT with non-literal offset expressions.

    Bug fix: When offset is a variable or expression (not a literal),
    it must be wrapped in int(m_num(...)) for proper type conversion.

    $TEXT(LABEL+offset) where offset is a variable expression.
    """

    def test_text_with_literal_offset(self, execute_mumps):
        """$TEXT with literal offset works correctly.

        $T(TEST+0) should return the label line itself.
        """
        code = """TEST W $T(TEST+0) Q"""
        result = execute_mumps(code)
        assert "TEST" in result.output
        assert result.success is True

    def test_text_with_variable_offset(self, execute_mumps):
        """$TEXT with variable as offset.

        S N=1 then $T(TEST+N) should work (not fail with type error).
        """
        code = """TEST S N=0 W $T(TEST+N) Q"""
        result = execute_mumps(code)
        assert "TEST" in result.output
        assert result.success is True

    def test_text_with_arithmetic_offset(self, execute_mumps):
        """$TEXT with arithmetic expression as offset.

        $T(TEST+(1-1)) should return line at TEST+0.
        """
        code = """TEST W $T(TEST+(1-1)) Q"""
        result = execute_mumps(code)
        assert "TEST" in result.output
        assert result.success is True

    def test_text_with_function_offset(self, execute_mumps):
        """$TEXT with function call as offset.

        $T(LABEL+$L("")) where $L("")=0, should return LABEL+0.
        """
        code = """TEST W $T(TEST+$L("")) Q"""
        result = execute_mumps(code)
        assert "TEST" in result.output
        assert result.success is True


# =============================================================================
# $TEXT Basic Functionality
# =============================================================================


@pytest.mark.codegen
@pytest.mark.spec017
class TestTextBasic:
    """Basic $TEXT functionality tests."""

    def test_text_of_current_line(self, execute_mumps):
        """$TEXT returns source of current routine line."""
        code = """TEST W $T(TEST) Q"""
        result = execute_mumps(code)
        # Should contain something from the TEST line
        assert result.success is True

    def test_text_plus_zero_returns_routine_name(self, execute_mumps):
        """$TEXT(+0) returns routine name preserving original case.

        Bug fix II-133: $TEXT(+0) was returning lowercase routine name
        because codegen lowercased _routine_name. Now preserves case.

        Per MUMPS standard, $T(+0) returns the routine name as it appears
        in the first line of source.
        """
        # The routine name comes from the first label
        code = """MYTEST W $T(+0) Q"""
        result = execute_mumps(code)
        # Should return "MYTEST" (preserving original case from first label)
        assert result.output == "MYTEST"
        assert result.success is True

    def test_text_plus_one(self, execute_mumps):
        """$TEXT(LABEL+1) returns line after label."""
        code = '''TEST W $T(TEST+1) Q
 W "This is line 2"'''
        result = execute_mumps(code)
        # Should work without error
        assert result.success is True

    def test_text_empty_for_nonexistent_line(self, execute_mumps):
        """$TEXT returns empty for line that doesn't exist."""
        code = """TEST W $T(TEST+999) Q"""
        result = execute_mumps(code)
        assert result.output == ""
        assert result.success is True


# =============================================================================
# $TEXT with Indirected Labels (Bug Fix)
# =============================================================================


@pytest.mark.codegen
class TestTextIndirection:
    """Tests for $TEXT with indirected label names.

    Bug fix (V1JST I-599/600): $TEXT(@X) and $TEXT(@X+N) where X contains
    a label name. The indirection evaluates X and uses its VALUE as the
    label name, rather than treating it as variable indirection.

    Example: S X="LABEL" then $T(@X) returns the source line at LABEL.
    """

    def test_text_indirect_simple(self, execute_mumps):
        """$T(@X) where X contains a label name.

        I-599 from MUGJ V1JST: Basic indirect label reference.
        """
        code = """TEST S X="L1" W $T(@X) Q
L1 W "LINE1" Q"""
        result = execute_mumps(code)
        # Should return the content of line L1
        assert "L1" in result.output
        assert result.success is True

    def test_text_indirect_with_offset(self, execute_mumps):
        """$T(@X+N) where X contains a label name.

        I-600 from MUGJ V1JST: Indirect label with offset.
        """
        code = """TEST S X="L1" W $T(@X+1) Q
L1 W "LINE1" Q
 W "LINE2" Q"""
        result = execute_mumps(code)
        # Should return the line AFTER L1 (offset +1)
        assert "LINE2" in result.output
        assert result.success is True

    def test_text_indirect_with_variable_offset(self, execute_mumps):
        """$T(@X+Y) where both X and Y are variables.

        Combined indirect label and variable offset.
        """
        code = """TEST S X="L1",Y=1 W $T(@X+Y) Q
L1 W "LINE1" Q
 W "LINE2" Q"""
        result = execute_mumps(code)
        assert "LINE2" in result.output
        assert result.success is True

    def test_text_indirect_nonexistent_label(self, execute_mumps):
        """$T(@X) returns empty when indirected label doesn't exist."""
        code = """TEST S X="NOTEXIST" W $T(@X) Q"""
        result = execute_mumps(code)
        assert result.output == ""
        assert result.success is True

    def test_text_indirect_with_zero_offset(self, execute_mumps):
        """$T(@X+0) returns the label line itself."""
        code = """TEST S X="TEST" W $T(@X+0) Q"""
        result = execute_mumps(code)
        # Should contain the TEST line
        assert "TEST" in result.output
        assert result.success is True

    def test_text_indirect_preserves_label_case(self, execute_mumps):
        """Indirect label lookup preserves case from variable value."""
        code = """TEST S X="MyLabel" W $T(@X) Q
MyLabel W "FOUND" Q"""
        result = execute_mumps(code)
        assert "MyLabel" in result.output or "FOUND" in result.output
        assert result.success is True
