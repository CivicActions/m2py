"""Tests for call-by-reference with MArray aliasing.

Phase 23: Verify that by-reference parameters pass the MArray object
directly so the callee can see/modify descendants, not just the scalar value.

Reference: MUMPS 1995 ANSI Standard, Section 8.2.3 (DO with parameters)
"""

import pytest


@pytest.mark.codegen
class TestCallByReferenceCodegen:
    """Codegen tests for by-reference parameter passing."""

    def test_byref_generates_scope_get_marray(self, generate_python):
        """By-reference generates _scope.get(name, MArray()) not m_var_value().

        When calling $$FN(.X), X should be passed as the MArray object
        so the callee gets the full tree including descendants.
        """
        code = 'TEST S X="val" W $$FN(.X) Q\nFN(A) Q A'
        result = generate_python(code)
        # Should pass MArray object, NOT m_var_value() wrapper
        assert "_scope.get('X', MArray())" in result
        assert "_byref=" in result

    def test_byref_parameter_aliasing(self, execute_mumps):
        """By-reference parameter creates alias - callee modifications visible.

        S X=1 D SUB(.X) ; Inside SUB, A is alias of X
        """
        code = "TEST\n S X=1\n D SUB(.X)\n W X\n Q\nSUB(A)\n S A=2\n Q"
        result = execute_mumps(code)
        assert result.output == "2"  # X was modified through alias A

    def test_byref_with_descendants(self, execute_mumps):
        """By-reference shares descendants - callee sees subtree.

        The key fix in Phase 23: pass MArray so $D(param) sees descendants.
        """
        code = "TEST\n S X=1,X(1)=2\n W $$FN(.X)\n Q\nFN(A)\n Q $D(A)\n"
        result = execute_mumps(code)
        # $D(A) should be 11 (value + descendants) since it's aliased to X
        assert result.output == "11"

    def test_byref_value_only_var(self, execute_mumps):
        """By-reference with value-only variable gives $D=1."""
        code = "TEST\n S X=1\n W $$FN(.X)\n Q\nFN(A)\n Q $D(A)\n"
        result = execute_mumps(code)
        # $D(A) should be 1 (value, no descendants)
        assert result.output == "1"
