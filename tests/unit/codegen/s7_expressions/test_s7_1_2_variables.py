"""Tests for Variables code generation (§7.1.2).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.2
"""

import pytest


@pytest.mark.codegen
class TestVariablesCodegen:
    """Codegen-level tests for variables code generation (§7.1.2)."""

    def test_local_variable_access(self, execute_mumps):
        """Local variable SET and READ works correctly (§7.1.2).

        YDB verified: S X=1 W X → "1"
        """
        result = execute_mumps("TEST\n S X=1\n W X\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_global_variable_access(self, execute_mumps):
        """Global variable SET and READ works correctly (§7.1.2).

        YDB verified: S ^G=1 W ^G → "1"
        """
        result = execute_mumps("TEST\n S ^G=1\n W ^G\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_subscripted_access(self, execute_mumps):
        """Subscripted variable access works correctly (§7.1.2).

        YDB verified: S A(1,2)=5 W A(1,2) → "5"
        """
        result = execute_mumps("TEST\n S A(1,2)=5\n W A(1,2)\n Q\n")
        assert result.output == "5"
        assert result.success is True

    def test_naked_global(self, execute_mumps):
        """Naked global reference uses stored reference (§7.1.2).

        YDB verified: S ^G(1)=1,^G(2)=2 W ^G(1),^(2) → "12"
        """
        result = execute_mumps("TEST\n S ^G(1)=1,^G(2)=2\n W ^G(1),^(2)\n Q\n")
        assert result.output == "12"
        assert result.success is True
