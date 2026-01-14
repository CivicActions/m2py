"""Tests for subscripted local variables (Spec 009 Phase 5 - User Story 3).

Subscripted local variables use MArray for MUMPS sparse array semantics,
where each node can have both a value AND children.

Acceptance Scenarios from spec.md:
1. S X(1)=1 W X(1) → "1" (single subscript)
2. S X(1,2)=2 W X(1,2) → "2" (nested subscript)
3. S X=1 S X(1)=2 W X," ",X(1) → "1 2" (value AND children)
4. S A("key")="value" W A("key") → "value" (string subscripts)
5. W X(99) → "" (undefined subscripted variable returns empty string)

Note: Tests use W X without ! since format control (!) codegen is not in scope.
Note: In strict MUMPS, reading undefined variables throws an error, but
m2py uses implicit $GET semantics (returns empty string) for simplicity.
"""

import pytest


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
