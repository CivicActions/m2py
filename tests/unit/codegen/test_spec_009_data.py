"""Tests for $DATA function (Spec 009 Phase 8 - User Story 6).

$DATA returns:
- 0: Node undefined, no descendants
- 1: Node defined (has value), no descendants
- 10: Node undefined, has descendants
- 11: Node defined AND has descendants

Acceptance Scenarios from spec.md:
1. W $D(UNDEF) → "0" (undefined variable)
2. S X=1 W $D(X) → "1" (value only)
3. S X(1)=1 W $D(X) → "10" (children only)
4. S X=1 S X(1)=2 W $D(X) → "11" (value and children)
5. S ^G=1 S ^G(1)=2 W $D(^G) → "11" (works on globals)

Note: Tests use W X without ! since format control (!) codegen is not in scope.
"""

import pytest


@pytest.mark.codegen
@pytest.mark.spec009
class TestDataLocalVariables:
    """Tests for $DATA with local variables."""

    def test_data_undefined_variable(self, execute_mumps):
        """Scenario 1: $DATA of undefined variable returns 0.

        W $D(UNDEF) → "0"
        """
        result = execute_mumps("TEST W $D(UNDEF) Q")
        assert result.output == "0"

    def test_data_value_only(self, execute_mumps):
        """Scenario 2: $DATA of variable with value only returns 1.

        S X=1 W $D(X) → "1"
        """
        result = execute_mumps("TEST S X=1 W $D(X) Q")
        assert result.output == "1"

    def test_data_children_only(self, execute_mumps):
        """Scenario 3: $DATA of variable with children only returns 10.

        S X(1)=1 W $D(X) → "10"
        X has a child X(1) but no value at X itself.
        """
        result = execute_mumps("TEST S X(1)=1 W $D(X) Q")
        assert result.output == "10"

    def test_data_value_and_children(self, execute_mumps):
        """Scenario 4: $DATA of variable with value AND children returns 11.

        S X=1 S X(1)=2 W $D(X) → "11"
        X has both a value and children.
        """
        result = execute_mumps("TEST S X=1 S X(1)=2 W $D(X) Q")
        assert result.output == "11"


@pytest.mark.codegen
@pytest.mark.spec009
class TestDataGlobalVariables:
    """Tests for $DATA with global variables."""

    def test_data_global_value_and_children(self, execute_mumps):
        """Scenario 5: $DATA works on globals with value AND children.

        S ^G=1 S ^G(1)=2 W $D(^G) → "11"
        """
        result = execute_mumps("TEST S ^G=1 S ^G(1)=2 W $D(^G) Q")
        assert result.output == "11"

    def test_data_global_undefined(self, execute_mumps):
        """$DATA of undefined global returns 0."""
        result = execute_mumps("TEST W $D(^UNDEFINED) Q")
        assert result.output == "0"

    def test_data_global_value_only(self, execute_mumps):
        """$DATA of global with value only returns 1."""
        result = execute_mumps("TEST S ^H=1 W $D(^H) Q")
        assert result.output == "1"

    def test_data_global_children_only(self, execute_mumps):
        """$DATA of global with children only returns 10."""
        result = execute_mumps("TEST S ^I(1)=1 W $D(^I) Q")
        assert result.output == "10"


@pytest.mark.codegen
@pytest.mark.spec009
class TestDataSubscriptedAccess:
    """Tests for $DATA with subscripted variable access."""

    def test_data_subscripted_local(self, execute_mumps):
        """$DATA of subscripted local variable."""
        result = execute_mumps("TEST S X(1)=1 S X(1,2)=2 W $D(X(1)) Q")
        # X(1) has value=1 and child X(1,2), so $D(X(1))=11
        assert result.output == "11"

    def test_data_subscripted_local_value_only(self, execute_mumps):
        """$DATA of leaf subscripted local variable."""
        result = execute_mumps("TEST S X(1,2)=2 W $D(X(1,2)) Q")
        # X(1,2) has value only, no children
        assert result.output == "1"

    def test_data_subscripted_global(self, execute_mumps):
        """$DATA of subscripted global variable."""
        result = execute_mumps("TEST S ^J(1)=1 S ^J(1,2)=2 W $D(^J(1)) Q")
        # ^J(1) has value=1 and child ^J(1,2), so $D(^J(1))=11
        assert result.output == "11"

    def test_data_undefined_subscript(self, execute_mumps):
        """$DATA of undefined subscript returns 0."""
        result = execute_mumps("TEST S X(1)=1 W $D(X(99)) Q")
        assert result.output == "0"
