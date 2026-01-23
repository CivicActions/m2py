"""Tests for $TEXT with expression offsets (Spec 017 Phase 6).

Tests the fix for $TEXT offset expression type conversion:
- Non-literal offset expressions need int(m_num(...)) wrapping

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
