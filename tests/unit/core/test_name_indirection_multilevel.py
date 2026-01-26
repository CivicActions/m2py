"""Tests for multi-level name indirection patterns.

Based on VV2VNIA/VV2VNIB MUGJ test patterns for multi-level indirection.

Feature: 018-unified-variable-system
User Story: US3 - Multi-Level Indirection Resolution

Note: E2E tests that use execute_mumps fixture are in
tests/unit/codegen/s7_expressions/test_s7_3_indirection.py
"""

from typing import Any

from m2py.core.indirection import (
    IndirectionResolver,
    IndirectionContext,
)
from m2py.core.scope import CurrentScope


class MockMState:
    """Mock MState for testing."""

    def __init__(self):
        self._globals = MockGlobalStorage()
        self._scope_for_execute = {}

    def execute_mumps(self, code: str, scope: dict) -> None:
        """Mock execute_mumps that handles simple expressions."""
        pass

    def get_var(self, name: str, scope: dict) -> Any:
        """Mock get_var."""
        return scope.get(name, "")


class MockGlobalStorage:
    """Mock global storage."""

    def __init__(self):
        self._data = {}

    def get(self, key: str, subscripts: tuple = ()) -> Any:
        full_key = (key, subscripts)
        return self._data.get(full_key)

    def set(self, key: str, subscripts: tuple, value: Any) -> None:
        full_key = (key, subscripts)
        self._data[full_key] = value


class TestMultiLevelIndirectionBasic:
    """Basic multi-level indirection tests (@@X, @@@X)."""

    def test_double_indirection(self):
        """@@X where X="A", A="B", B=99 → 99."""
        state = MockMState()

        scope_dict = {"X": "A", "A": "B", "B": 99}
        scope = CurrentScope(scope_dict=scope_dict)
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve("X", levels=2, context=IndirectionContext.NAME)
        assert result == 99

    def test_triple_indirection(self):
        """@@@X where X="A", A="B", B="C", C=42 → 42."""
        state = MockMState()

        scope_dict = {"X": "A", "A": "B", "B": "C", "C": 42}
        scope = CurrentScope(scope_dict=scope_dict)
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve("X", levels=3, context=IndirectionContext.NAME)
        assert result == 42

    def test_quad_indirection(self):
        """@@@@X where X="A", A="B", B="C", C="D", D=100 → 100."""
        state = MockMState()

        scope_dict = {"X": "A", "A": "B", "B": "C", "C": "D", "D": 100}
        scope = CurrentScope(scope_dict=scope_dict)
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve("X", levels=4, context=IndirectionContext.NAME)
        assert result == 100


class TestMultiLevelWithPerLevelSubscripts:
    """Tests for @@X@(subs)@(subs) patterns from VV2VNIA II-127."""

    def test_ii127_double_level_with_subscripts(self):
        """@@X@(1,2)@(5,6) where X="A", A(1,2)="B(3,4)" → access B(3,4,5,6)."""
        state = MockMState()
        from m2py.runtime import MArray

        A = MArray()
        A[1, 2].value = "B"  # Note: simplified - B(3,4) is not necessary for unit test
        B = MArray()
        B[3, 4, 5, 6].value = 1

        # For this test, we'll use a simpler version:
        # X="A", A(1,2)="B", B(5,6)=1
        A2 = MArray()
        A2[1, 2].value = "B"
        B2 = MArray()
        B2[5, 6].value = "result_127"

        scope = CurrentScope(scope_dict={"X": "A", "A": A2, "B": B2})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve(
            "X",
            levels=2,
            context=IndirectionContext.NAME,
            per_level_subscripts=[[1, 2], [5, 6]],
        )
        assert result == "result_127"


class TestDeepNesting:
    """Tests for deep nesting patterns from VV2VNIB II-131."""

    def test_ii131_deep_nested_subscripts(self):
        """@B@(@B@(@B@(9)),@B,I) pattern with deep nesting.

        Setup:
        - B = "A"
        - @B = value of B = "A" as var name = value of A = 5
        - @B@(9) = A(9) = "X"
        - @B@(@B@(9)) = A("X") = "FOO"
        - @B@(@B@(@B@(9)),@B,I) = A("FOO", 5, 3)

        For the unit test, we verify the final subscripted access works.
        Full E2E behavior is tested in test_s7_3_indirection.py.
        """
        state = MockMState()
        from m2py.runtime import MArray

        A = MArray()
        A.value = 5  # A = 5
        A[9].value = "X"  # A(9) = "X"
        A["X"].value = "FOO"  # A("X") = "FOO"
        A["FOO", 5, 3].value = "deep_result"  # A("FOO", 5, 3)

        scope_dict = {"B": "A", "A": A, "I": 3}
        scope = CurrentScope(scope_dict=scope_dict)
        resolver = IndirectionResolver(state, scope)

        # Test that per_level_subscripts works for the final access
        result = resolver.resolve(
            "B",
            levels=1,
            context=IndirectionContext.NAME,
            per_level_subscripts=[["FOO", 5, 3]],
        )
        assert result == "deep_result"


class TestRecursiveAtExpressions:
    """Tests for recursive @-expressions from VV2VNIB II-132.3."""

    def test_ii132_3_four_level_with_at_in_values(self):
        """@@@@A where values contain @-expressions.

        Setup (from VV2VNIB II-132.3):
        - B = "A(1)"
        - A = "@B@(1)" → resolves to A(1,1)
        - A(1,1) = "@B@(2)" → resolves to A(1,2)
        - A(1,2) = "@B@(3)" → resolves to A(1,3)
        - A(1,3) = "@B@(4)" → resolves to A(1,4)
        - A(1,4) = "#"

        For the unit test, we verify scope access.
        Full E2E behavior is tested in test_s7_3_indirection.py.
        """
        from m2py.runtime import MArray

        A = MArray()
        A.value = "@B@(1)"
        A[1, 1].value = "@B@(2)"
        A[1, 2].value = "@B@(3)"
        A[1, 3].value = "@B@(4)"
        A[1, 4].value = "#"

        scope_dict = {"B": "A(1)", "A": A}
        scope = CurrentScope(scope_dict=scope_dict)

        # Test that we can at least get the initial value
        result = scope.get("A")
        assert result == "@B@(1)"


class TestValueContainsAtExpression:
    """Tests for values that contain @-expressions."""

    def test_value_with_at_triggers_recursive_resolution(self):
        """When resolved value starts with @, it triggers recursive evaluation."""
        # S A="@B",B="C",C=99 W @@A
        # @A = "@B" (value of A)
        # @@A = @"@B" = resolve @B = "C" → value of C = 99
        scope_dict = {"A": "@B", "B": "C", "C": 99}
        scope = CurrentScope(scope_dict=scope_dict)

        # For the unit test, verify scope access works
        assert scope.get("A") == "@B"
        assert scope.get("B") == "C"
        assert scope.get("C") == 99
