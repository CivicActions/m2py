"""Tests for global variable SET/READ (Spec 009 Phase 6 - User Story 4).

Global variables use GlobalStorageBackend for storage, with InMemoryGlobalStorage
as the default backend. The generated code calls _rt.globals.set() and _rt.globals.get().

Acceptance Scenarios from spec.md:
1. S ^A=1 W ^A → "1" (simple global SET/READ)
2. S ^A(1,2)=1 W ^A(1,2) → "1" (subscripted global)
3. S ^G=1 S ^G(1)=2 W ^G," ",^G(1) → "1 2" (value AND children)
4. W ^UNDEFINED → "" (undefined global returns empty string - implicit $GET semantics)
5. S ^DATA("NAME")="John" W ^DATA("NAME") → "John" (string subscripts)

Note: Tests use W X without ! since format control (!) codegen is not in scope.
Note: In strict MUMPS, reading undefined global throws GVUNDEF error, but
m2py uses implicit $GET semantics (returns empty string) for simplicity.
"""

import pytest


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
