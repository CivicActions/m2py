"""Tests for ARGUMENT indirection resolution.

Feature: 018-unified-variable-system (Phase 4, User Story 2)
Task: T045 - V1IDARG patterns for argument indirection

Argument indirection (in IF, FOR conditions) evaluates the resolved value
as a MUMPS EXPRESSION, not as a variable name to look up. This is the
critical distinction from Name Indirection (in SET, WRITE).

Key test: S A="1=0" I @A
  - Name indirection interpretation: Look up variable named "1=0" → ERROR
  - Argument indirection interpretation: Evaluate "1=0" as expression → FALSE

Challenge 6 Bug Fix: Previously, m2py returned the STRING "1=0" to m_truth(),
which converted to 1 (TRUE) because the string starts with "1".
"""

import pytest

from m2py.core.indirection import IndirectionContext, IndirectionResolver
from m2py.core.scope import CurrentScope
from m2py.runtime import MArray


class MockState:
    """Mock MState for testing IndirectionResolver."""

    def __init__(self):
        self._scope_for_execute: dict = {}

    def execute_mumps(self, code: str, scope: dict) -> None:
        """Execute MUMPS code to evaluate expression.

        For testing, we only need to handle simple expressions.
        Complex expression evaluation uses the real runtime.
        """
        # Parse S TEMP=expr format
        # The IndirectionResolver uses %ARGINDIRECT as temp var (becomes _pct_ARGINDIRECT)
        if code.startswith("S %ARGINDIRECT="):
            expr = code[len("S %ARGINDIRECT=") :]
            # Evaluate simple expressions
            result = self._eval_simple_expr(expr, scope)
            from m2py.runtime import MArray

            ma = MArray()
            ma.value = result
            scope["_pct_ARGINDIRECT"] = ma

    def _eval_simple_expr(self, expr: str, scope: dict) -> int | str:
        """Evaluate simple MUMPS expressions for testing."""
        expr = expr.strip()

        # Handle equality comparison (1=0 → 0, 1=1 → 1)
        if "=" in expr:
            parts = expr.split("=", 1)
            left = self._get_value(parts[0].strip(), scope)
            right = self._get_value(parts[1].strip(), scope)
            return 1 if self._mumps_equal(left, right) else 0

        # Handle greater-than comparison (X>5)
        if ">" in expr:
            parts = expr.split(">", 1)
            left = self._get_value(parts[0].strip(), scope)
            right = self._get_value(parts[1].strip(), scope)
            return 1 if float(self._to_num(left)) > float(self._to_num(right)) else 0

        # Handle less-than comparison
        if "<" in expr:
            parts = expr.split("<", 1)
            left = self._get_value(parts[0].strip(), scope)
            right = self._get_value(parts[1].strip(), scope)
            return 1 if float(self._to_num(left)) < float(self._to_num(right)) else 0

        # Handle arithmetic (1+1 → 2)
        if "+" in expr:
            parts = expr.split("+", 1)
            left = self._to_num(self._get_value(parts[0].strip(), scope))
            right = self._to_num(self._get_value(parts[1].strip(), scope))
            return int(left + right)

        # Simple value
        return self._get_value(expr, scope)

    def _get_value(self, name: str, scope: dict) -> str | int:
        """Get value from scope or parse as literal."""
        # Numeric literal
        try:
            return int(name)
        except ValueError:
            try:
                return float(name)
            except ValueError:
                pass

        # Variable reference
        if name in scope:
            val = scope[name]
            if isinstance(val, MArray):
                return val.value or ""
            return val

        # String literal
        if name.startswith('"') and name.endswith('"'):
            return name[1:-1]

        return name

    def _to_num(self, val) -> float:
        """Convert to number (MUMPS semantics)."""
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val)
        # Extract leading numeric portion
        result = ""
        for c in s:
            if c.isdigit() or c == "." or (c == "-" and not result):
                result += c
            else:
                break
        return float(result) if result else 0.0

    def _mumps_equal(self, left, right) -> bool:
        """MUMPS equality comparison."""
        # Try numeric comparison first
        try:
            return float(self._to_num(left)) == float(self._to_num(right))
        except (ValueError, TypeError):
            return str(left) == str(right)


@pytest.fixture
def mock_state():
    """Create mock MState for testing."""
    return MockState()


@pytest.fixture
def scope():
    """Create CurrentScope for testing."""
    scope_dict = {}
    return CurrentScope(scope_dict=scope_dict)


@pytest.fixture
def resolver(mock_state, scope):
    """Create IndirectionResolver with mock state."""
    return IndirectionResolver(mock_state, scope)


class TestArgumentIndirectionBasic:
    """Basic argument indirection tests (V1IDARG patterns)."""

    def test_numeric_literal_true(self, resolver, scope):
        """I @A where A="1" evaluates to TRUE.

        V1IDARG I-417: Simple numeric value.
        The value "1" is evaluated as an expression, resulting in 1 (TRUE).
        """
        scope.set("A", "1")
        result = resolver.resolve("A", 1, IndirectionContext.ARGUMENT)
        # MUMPS truthiness: non-zero is TRUE (1)
        assert result == 1

    def test_numeric_literal_zero(self, resolver, scope):
        """I @A where A="0" evaluates to FALSE.

        The value "0" is evaluated as an expression, resulting in 0 (FALSE).
        """
        scope.set("A", "0")
        result = resolver.resolve("A", 1, IndirectionContext.ARGUMENT)
        assert result == 0

    def test_expression_equality_false(self, resolver, scope):
        """I @A where A="1=0" evaluates to FALSE.

        **CRITICAL BUG FIX** (Challenge 6):
        - OLD behavior: m_truth("1=0") → 1 (TRUE) because string starts with "1"
        - CORRECT behavior: Evaluate "1=0" → 0 (FALSE) because 1 ≠ 0
        """
        scope.set("A", "1=0")
        result = resolver.resolve("A", 1, IndirectionContext.ARGUMENT)
        # 1=0 evaluates to FALSE (0) in MUMPS
        assert result == 0

    def test_expression_equality_true(self, resolver, scope):
        """I @A where A="1=1" evaluates to TRUE.

        The expression "1=1" evaluates to 1 (TRUE).
        """
        scope.set("A", "1=1")
        result = resolver.resolve("A", 1, IndirectionContext.ARGUMENT)
        assert result == 1

    def test_expression_with_variable(self, resolver, scope):
        """I @A where A="X>5" and X=10 evaluates to TRUE.

        T047: Expression references another variable.
        """
        scope.set("A", "X>5")
        scope.set("X", "10")  # Store as string to match MUMPS semantics
        result = resolver.resolve("A", 1, IndirectionContext.ARGUMENT)
        # X>5 with X=10 → 10>5 → TRUE
        assert result == 1

    def test_expression_with_variable_false(self, resolver, scope):
        """I @A where A="X>5" and X=3 evaluates to FALSE."""
        scope.set("A", "X>5")
        scope.set("X", "3")
        result = resolver.resolve("A", 1, IndirectionContext.ARGUMENT)
        # X>5 with X=3 → 3>5 → FALSE
        assert result == 0

    def test_empty_string_true(self, resolver, scope):
        """I @A where A="" evaluates to TRUE (YDB-specific).

        T052: Empty string in argument context is TRUE.
        Per YDB behavior, `I @A` where A="" returns TRUE,
        even though `I ""` returns FALSE. This appears to be
        because successful indirection resolution (even to empty) is truthy.

        Note: This differs from direct empty string: `I ""` → FALSE
        """
        scope.set("A", "")
        result = resolver.resolve("A", 1, IndirectionContext.ARGUMENT)
        # YDB treats empty argument indirection as TRUE
        assert result == 1


class TestArgumentIndirectionMultiLevel:
    """Multi-level argument indirection tests."""

    def test_two_level_argument_indirection(self, resolver, scope):
        """I @@A resolves through two levels then evaluates.

        V1IDARG I-420 pattern: @@X resolves X→value→value, then evaluates.
        """
        scope.set("A", "B")
        scope.set("B", "1=1")
        result = resolver.resolve("A", 2, IndirectionContext.ARGUMENT)
        # A→"B"→"1=1", then evaluate "1=1" → 1 (TRUE)
        assert result == 1

    def test_three_level_argument_indirection(self, resolver, scope):
        """I @@@A resolves through three levels then evaluates.

        V1IDARG I-421 pattern.
        """
        scope.set("A", "B")
        scope.set("B", "C")
        scope.set("C", "5>3")
        result = resolver.resolve("A", 3, IndirectionContext.ARGUMENT)
        # A→"B"→"C"→"5>3", then evaluate "5>3" → 1 (TRUE)
        assert result == 1


class TestArgumentIndirectionConvenienceMethod:
    """Tests for resolve_argument_indirection() convenience method."""

    def test_convenience_method_equals_resolve(self, resolver, scope):
        """resolve_argument_indirection() is equivalent to resolve() with ARGUMENT."""
        scope.set("A", "1=0")
        result1 = resolver.resolve_argument_indirection("A")
        result2 = resolver.resolve("A", 1, IndirectionContext.ARGUMENT)
        assert result1 == result2

    def test_convenience_method_simple(self, resolver, scope):
        """resolve_argument_indirection() works for simple case."""
        scope.set("A", "1+1")
        result = resolver.resolve_argument_indirection("A")
        # 1+1 = 2, which is truthy
        assert result == 2


class TestArgumentVsNameIndirection:
    """Tests contrasting argument vs name indirection behavior."""

    def test_name_indirection_looks_up_variable(self, resolver, scope):
        """Name indirection @A where A="X" looks up value of X.

        For NAME context: @A → A="X" → look up X's value.
        """
        scope.set("A", "X")
        scope.set("X", "42")
        result = resolver.resolve("A", 1, IndirectionContext.NAME)
        # NAME context: Look up variable X, get "42"
        assert result == "42"

    def test_argument_indirection_evaluates_expression(self, resolver, scope):
        """Argument indirection @A where A="X" evaluates X as expression.

        For ARGUMENT context: @A → A="X" → evaluate "X" as expression.
        If X is defined, its value is used in the evaluation.
        """
        scope.set("A", "X")
        scope.set("X", "42")
        result = resolver.resolve("A", 1, IndirectionContext.ARGUMENT)
        # ARGUMENT context: Evaluate "X" which gets X's value (42)
        # Then truthiness of 42 is 1 (TRUE)
        assert result == 1

    def test_critical_difference_expression_evaluation(self, resolver, scope):
        """Demonstrate the critical difference in "1=0" handling.

        This is the Challenge 6 bug fix test.
        - If we just looked up "1=0" as a variable name → UNDEFINED error
        - If we passed "1=0" directly to m_truth → TRUE (WRONG)
        - If we EVALUATE "1=0" as expression → FALSE (CORRECT)
        """
        scope.set("A", "1=0")

        # NAME indirection would try to look up variable named "1=0"
        # which would fail with VAREXPECTED since "1=0" is not a valid name

        # ARGUMENT indirection evaluates "1=0" as an expression
        result = resolver.resolve("A", 1, IndirectionContext.ARGUMENT)
        assert result == 0, "1=0 should evaluate to FALSE, not be treated as string"
