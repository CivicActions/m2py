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


@pytest.mark.codegen
class TestExtendedGlobalsCodegen:
    """Codegen-level tests for extended global references (YDB extension).

    Extended globals use pipe (^|"env"|X) or bracket (^["env"]X) syntax
    to reference globals in different environments/databases.
    These are YDB-specific features that cannot be transpiled to pure Python.

    Spec 015: Document YDB extensions as not supported with proper test coverage.
    """

    def test_extended_global_pipe_raises_not_implemented(self, generate_python):
        """Extended global with pipe syntax raises NotImplementedError.

        The ^|"env"|X syntax selects a global from a specific environment.
        This is a YDB extension for multi-database access.
        """
        code = 'TEST\n S ^|"env"|X=1\n Q\n'
        with pytest.raises(NotImplementedError, match="ExtendedGlobalPipe"):
            generate_python(code)

    def test_extended_global_bracket_raises_not_implemented(self, generate_python):
        """Extended global with bracket syntax raises NotImplementedError.

        The ^["env"]X syntax is an alternative way to select a global
        from a specific environment. This is a YDB extension.
        """
        code = 'TEST\n S ^["env"]X=1\n Q\n'
        with pytest.raises(NotImplementedError, match="ExtendedGlobalBracket"):
            generate_python(code)

    def test_extended_global_pipe_with_subscripts_raises_not_implemented(
        self, generate_python
    ):
        """Extended global with subscripts raises NotImplementedError."""
        code = 'TEST\n S ^|"env"|X(1,2)=1\n Q\n'
        with pytest.raises(NotImplementedError, match="ExtendedGlobalPipe"):
            generate_python(code)

    def test_extended_global_bracket_with_subscripts_raises_not_implemented(
        self, generate_python
    ):
        """Extended global bracket with subscripts raises NotImplementedError."""
        code = 'TEST\n S ^["env"]X(1,2)=1\n Q\n'
        with pytest.raises(NotImplementedError, match="ExtendedGlobalBracket"):
            generate_python(code)

    def test_extended_global_in_expression_raises_not_implemented(
        self, generate_python
    ):
        """Extended global in expression context raises NotImplementedError."""
        code = 'TEST\n W ^|"env"|X\n Q\n'
        with pytest.raises(NotImplementedError, match="ExtendedGlobalPipe"):
            generate_python(code)
