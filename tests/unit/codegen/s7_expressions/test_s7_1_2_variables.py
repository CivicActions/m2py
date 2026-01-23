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

    def test_extended_global_bracket_set_supported(self, generate_python):
        """Extended global with bracket syntax is now supported.

        The ^["env"]X syntax selects a global from a specific environment.
        For m2py, the environment is ignored and the global is accessed normally.
        """
        code = 'TEST\n S ^["env"]X=1\n Q\n'
        # Should not raise - environment is ignored, treated as regular global
        result = generate_python(code)
        assert "_rt.globals.set('X', (), str(1))" in result

    def test_extended_global_pipe_with_subscripts_raises_not_implemented(
        self, generate_python
    ):
        """Extended global with subscripts raises NotImplementedError."""
        code = 'TEST\n S ^|"env"|X(1,2)=1\n Q\n'
        with pytest.raises(NotImplementedError, match="ExtendedGlobalPipe"):
            generate_python(code)

    def test_extended_global_bracket_with_subscripts_supported(self, generate_python):
        """Extended global bracket with subscripts is now supported.

        For m2py, the environment is ignored and the global is accessed normally.
        """
        code = 'TEST\n S ^["env"]X(1,2)=1\n Q\n'
        result = generate_python(code)
        assert "_rt.globals.set('X'," in result

    def test_extended_global_in_expression_raises_not_implemented(
        self, generate_python
    ):
        """Extended global in expression context raises NotImplementedError."""
        code = 'TEST\n W ^|"env"|X\n Q\n'
        with pytest.raises(NotImplementedError, match="ExtendedGlobalPipe"):
            generate_python(code)


# =============================================================================
# Global Variables Tests (consolidated from test_spec_009_globals.py)
# =============================================================================


@pytest.mark.codegen
@pytest.mark.spec009
class TestGlobalVariablesBasic:
    """Tests for basic global variable operations."""

    def test_simple_global_set_read(self, execute_mumps):
        """Scenario 1: Simple global SET and READ.

        S ^A=1 W ^A → "1"
        """
        result = execute_mumps("TEST S ^A=1 W ^A Q")
        assert result.output == "1"

    def test_subscripted_global_set_read(self, execute_mumps):
        """Scenario 2: Subscripted global SET and READ.

        S ^A(1,2)=1 W ^A(1,2) → "1"
        """
        result = execute_mumps("TEST S ^A(1,2)=1 W ^A(1,2) Q")
        assert result.output == "1"

    def test_global_value_and_children(self, execute_mumps):
        """Scenario 3: Global can have both root value AND children.

        S ^G=1 S ^G(1)=2 W ^G," ",^G(1) → "1 2"
        """
        result = execute_mumps('TEST S ^G=1 S ^G(1)=2 W ^G," ",^G(1) Q')
        assert result.output == "1 2"

    def test_undefined_global_returns_empty(self, execute_mumps):
        """Scenario 4: Undefined global returns empty string.

        W ^UNDEFINED → "" (m2py uses implicit $GET semantics)
        """
        result = execute_mumps("TEST W ^UNDEFINED Q")
        assert result.output == ""

    def test_string_subscripts_global(self, execute_mumps):
        """Scenario 5: String subscripts work correctly.

        S ^DATA("NAME")="John" W ^DATA("NAME") → "John"
        """
        result = execute_mumps('TEST S ^DATA("NAME")="John" W ^DATA("NAME") Q')
        assert result.output == "John"


@pytest.mark.codegen
@pytest.mark.spec009
class TestGlobalVariablesEdgeCases:
    """Edge case tests for global variables."""

    def test_multiple_subscripts(self, execute_mumps):
        """Multiple levels of subscripts work correctly."""
        result = execute_mumps("TEST S ^X(1,2,3)=5 W ^X(1,2,3) Q")
        assert result.output == "5"

    def test_mixed_subscript_types(self, execute_mumps):
        """Mix of numeric and string subscripts."""
        result = execute_mumps('TEST S ^X(1,"a",2)="mixed" W ^X(1,"a",2) Q')
        assert result.output == "mixed"

    def test_set_multiple_subscripts_same_global(self, execute_mumps):
        """Set multiple subscripted elements in same global."""
        result = execute_mumps('TEST S ^X(1)=1 S ^X(2)=2 W ^X(1),"-",^X(2) Q')
        assert result.output == "1-2"

    def test_read_undefined_nested_returns_empty(self, execute_mumps):
        """Undefined nested subscript returns empty string."""
        result = execute_mumps("TEST S ^X(1)=1 W ^X(1,2) Q")
        assert result.output == ""

    def test_value_at_root_and_deep_subscript(self, execute_mumps):
        """Set value at root and at deep subscript level."""
        result = execute_mumps(
            'TEST S ^X="root" S ^X(1,2,3)="deep" W ^X,"-",^X(1,2,3) Q'
        )
        assert result.output == "root-deep"


# =============================================================================
# Subscripted Local Variables Tests (consolidated from test_spec_009_subscripted.py)
# =============================================================================


@pytest.mark.codegen
@pytest.mark.spec009
class TestSubscriptedLocalsBasic:
    """Tests for basic subscripted local variable operations."""

    def test_single_subscript_set_write(self, execute_mumps):
        """Scenario 1: Set and write with single subscript.

        S X(1)=1 W X(1) → "1"
        """
        result = execute_mumps("TEST S X(1)=1 W X(1) Q")
        assert result.output == "1"

    def test_nested_subscript_set_write(self, execute_mumps):
        """Scenario 2: Set and write with nested subscripts.

        S X(1,2)=2 W X(1,2) → "2"
        """
        result = execute_mumps("TEST S X(1,2)=2 W X(1,2) Q")
        assert result.output == "2"

    def test_value_and_children(self, execute_mumps):
        """Scenario 3: Variable can have both root value AND children.

        S X=1 S X(1)=2 W X," ",X(1) → "1 2"
        """
        result = execute_mumps('TEST S X=1 S X(1)=2 W X," ",X(1) Q')
        assert result.output == "1 2"

    def test_string_subscripts(self, execute_mumps):
        """Scenario 4: String subscripts work correctly.

        S A("key")="value" W A("key") → "value"
        """
        result = execute_mumps('TEST S A("key")="value" W A("key") Q')
        assert result.output == "value"

    def test_undefined_subscripted_returns_empty(self, execute_mumps):
        """Scenario 5: Undefined subscripted variable returns empty string.

        W X(99) → "" (m2py uses implicit $GET semantics)
        """
        result = execute_mumps("TEST W X(99) Q")
        assert result.output == ""


@pytest.mark.codegen
@pytest.mark.spec009
class TestSubscriptedLocalsEdgeCases:
    """Edge case tests for subscripted local variables."""

    def test_multiple_subscripts(self, execute_mumps):
        """Multiple levels of subscripts work correctly."""
        result = execute_mumps("TEST S X(1,2,3)=5 W X(1,2,3) Q")
        assert result.output == "5"

    def test_mixed_subscript_types(self, execute_mumps):
        """Mix of numeric and string subscripts."""
        result = execute_mumps('TEST S X(1,"a",2)="mixed" W X(1,"a",2) Q')
        assert result.output == "mixed"

    def test_set_multiple_subscripts_same_array(self, execute_mumps):
        """Set multiple subscripted elements in same array."""
        result = execute_mumps('TEST S X(1)=1 S X(2)=2 W X(1),"-",X(2) Q')
        assert result.output == "1-2"

    def test_write_undefined_nested_returns_empty(self, execute_mumps):
        """Undefined nested subscript returns empty string."""
        result = execute_mumps("TEST S X(1)=1 W X(1,2) Q")
        assert result.output == ""

    def test_value_at_root_and_deep_subscript(self, execute_mumps):
        """Set value at root and at deep subscript level."""
        result = execute_mumps('TEST S X="root" S X(1,2,3)="deep" W X,"-",X(1,2,3) Q')
        assert result.output == "root-deep"
