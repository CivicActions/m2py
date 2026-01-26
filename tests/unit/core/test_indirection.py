"""Unit tests for IndirectionResolver.

Tests the unified indirection resolution logic per
contracts/indirection-resolver.md.

Feature: 018-unified-variable-system
Requirements: FR-010 through FR-022
"""

import pytest
from typing import Any

from m2py.core.indirection import (
    IndirectionResolver,
    IndirectionContext,
    VarExpectedError,
)
from m2py.core.scope import CurrentScope


class MockMState:
    """Mock MState for testing."""

    def __init__(self):
        self._globals = MockGlobalStorage()
        self._scope_for_execute = {}

    def execute_mumps(self, code: str, scope: dict) -> None:
        """Mock execute_mumps that handles simple expressions."""
        # Parse simple SET commands: S VAR=EXPR
        if code.startswith("S "):
            rest = code[2:]
            eq_pos = rest.find("=")
            if eq_pos > 0:
                var_name = rest[:eq_pos].strip()
                expr = rest[eq_pos + 1 :].strip()
                # Evaluate simple expressions
                result = self._eval_expr(expr, scope)
                scope[var_name] = result

    def _eval_expr(self, expr: str, scope: dict) -> Any:
        """Evaluate simple MUMPS expressions."""
        expr = expr.strip()

        # Numeric literal
        try:
            if "." in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass

        # String literal
        if expr.startswith('"') and expr.endswith('"'):
            return expr[1:-1]

        # Simple comparison: X=Y or X>Y etc
        for op in ["=", ">", "<", "'=", ">=", "<="]:
            if op in expr:
                left, right = expr.split(op, 1)
                left_val = self._eval_expr(left.strip(), scope)
                right_val = self._eval_expr(right.strip(), scope)
                if op == "=":
                    return 1 if str(left_val) == str(right_val) else 0
                elif op == "'=":
                    return 1 if str(left_val) != str(right_val) else 0
                elif op == ">":
                    return 1 if float(left_val or 0) > float(right_val or 0) else 0
                elif op == "<":
                    return 1 if float(left_val or 0) < float(right_val or 0) else 0

        # Variable reference
        if expr[0].isalpha() or expr[0] == "%":
            return scope.get(expr, "")

        return 0

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


class TestIndirectionContextEnum:
    """Tests for IndirectionContext enum."""

    def test_name_context(self):
        """NAME context for variable lookups."""
        assert IndirectionContext.NAME.value == "name"

    def test_argument_context(self):
        """ARGUMENT context for expression evaluation."""
        assert IndirectionContext.ARGUMENT.value == "argument"

    def test_subscript_context(self):
        """SUBSCRIPT context for subscript values."""
        assert IndirectionContext.SUBSCRIPT.value == "subscript"

    def test_pattern_context(self):
        """PATTERN context for pattern match."""
        assert IndirectionContext.PATTERN.value == "pattern"


class TestBasicNameIndirection:
    """Tests for basic name indirection (@X)."""

    def test_single_level_indirection(self):
        """@X where X="Y", Y=5 → 5."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "Y", "Y": 5})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve("X", levels=1, context=IndirectionContext.NAME)
        assert result == 5

    def test_two_level_indirection(self):
        """@@X where X="Y", Y="Z", Z=99 → 99."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "Y", "Y": "Z", "Z": 99})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve("X", levels=2, context=IndirectionContext.NAME)
        assert result == 99

    def test_three_level_indirection(self):
        """@@@X where X→Y→Z→W, W=42 → 42."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "Y", "Y": "Z", "Z": "W", "W": 42})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve("X", levels=3, context=IndirectionContext.NAME)
        assert result == 42


class TestNameIndirectionConvenience:
    """Tests for resolve_name_indirection() convenience method."""

    def test_simple_name_indirection(self):
        """resolve_name_indirection("X") equivalent to resolve(X, 1, NAME)."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "Y", "Y": "value"})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve_name_indirection("X")
        assert result == "value"

    def test_name_indirection_with_subscripts(self):
        """resolve_name_indirection("X", [1,2]) for @X(1,2) form."""
        state = MockMState()
        from m2py.runtime import MArray

        arr = MArray()
        arr[1, 2].value = "hello"
        scope = CurrentScope(scope_dict={"X": "A", "A": arr})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve_name_indirection("X", [1, 2])
        assert result == "hello"


class TestArgumentIndirection:
    """Tests for argument indirection (Challenge 6 fix)."""

    def test_argument_indirection_evaluates_expression(self):
        """@A where A="1=0" → FALSE (Challenge 6 bug fix)."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"A": "1=0"})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve("A", levels=1, context=IndirectionContext.ARGUMENT)
        # "1=0" evaluates to FALSE (0)
        assert result == 0

    def test_argument_indirection_true_expression(self):
        """@A where A="1=1" → TRUE."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"A": "1=1"})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve("A", levels=1, context=IndirectionContext.ARGUMENT)
        assert result == 1

    def test_argument_indirection_with_variable(self):
        """@A where A="X>5" and X=10 → TRUE."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"A": "X>5", "X": 10})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve("A", levels=1, context=IndirectionContext.ARGUMENT)
        assert result == 1

    def test_argument_indirection_empty_string(self):
        """@A where A="" → FALSE (empty string)."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"A": ""})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve("A", levels=1, context=IndirectionContext.ARGUMENT)
        assert result == 0


class TestArgumentIndirectionConvenience:
    """Tests for resolve_argument_indirection() convenience method."""

    def test_challenge_6_fix(self):
        """Critical bug fix: I @A where A="1=0" must be FALSE."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"A": "1=0"})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve_argument_indirection("A")
        assert result == 0  # FALSE, not truthy

    def test_variable_comparison(self):
        """I @A where A="X>5", X=10 → TRUE."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"A": "X>5", "X": 10})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve_argument_indirection("A")
        assert result == 1


class TestVarExpectedError:
    """Tests for NAME context variable validation."""

    def test_expression_in_name_context_raises(self):
        """NAME context with expression "1+1" raises VarExpectedError."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"A": "1+1"})
        resolver = IndirectionResolver(state, scope)

        with pytest.raises(VarExpectedError):
            resolver.resolve("A", levels=1, context=IndirectionContext.NAME)

    def test_empty_string_in_name_context_raises(self):
        """NAME context with empty string raises VarExpectedError."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"A": ""})
        resolver = IndirectionResolver(state, scope)

        with pytest.raises(VarExpectedError):
            resolver.resolve("A", levels=1, context=IndirectionContext.NAME)


class TestPerLevelSubscripts:
    """Tests for per-level subscript application (@X@(1,2)@(3,4))."""

    def test_single_level_with_subscripts(self):
        """@X@(1,2) where X="A" → access A(1,2)."""
        state = MockMState()
        from m2py.runtime import MArray

        arr = MArray()
        arr[1, 2].value = "found"
        scope = CurrentScope(scope_dict={"X": "A", "A": arr})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve(
            "X",
            levels=1,
            context=IndirectionContext.NAME,
            per_level_subscripts=[[1, 2]],
        )
        assert result == "found"


class TestRecursiveAtExpression:
    """Tests for recursive @-expression handling."""

    def test_value_with_at_prefix(self):
        """Value starting with @ is recursively resolved."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"A": "@B", "B": "C", "C": 99})
        resolver = IndirectionResolver(state, scope)

        # @A resolves: A→"@B"; @B contains @, recurse: B→"C"; return C value
        result = resolver.resolve("A", levels=1, context=IndirectionContext.NAME)
        assert result == 99


class TestEvaluateExpression:
    """Tests for evaluate_expression method."""

    def test_numeric_literal(self):
        """Numeric literals evaluate correctly."""
        state = MockMState()
        scope = CurrentScope(scope_dict={})
        resolver = IndirectionResolver(state, scope)

        assert resolver.evaluate_expression("42") == 42
        assert resolver.evaluate_expression("3.14") == 3.14
        assert resolver.evaluate_expression("0") == 0

    def test_empty_string_is_false(self):
        """Empty string evaluates to FALSE (0)."""
        state = MockMState()
        scope = CurrentScope(scope_dict={})
        resolver = IndirectionResolver(state, scope)

        assert resolver.evaluate_expression("") == 0
        assert resolver.evaluate_expression("  ") == 0

    def test_comparison_expression(self):
        """Comparison expressions evaluate correctly."""
        state = MockMState()
        scope = CurrentScope(scope_dict={})
        resolver = IndirectionResolver(state, scope)

        assert resolver.evaluate_expression("1=1") == 1
        assert resolver.evaluate_expression("1=0") == 0
        assert resolver.evaluate_expression("5>3") == 1
        assert resolver.evaluate_expression("2<1") == 0


class TestSubscriptContext:
    """Tests for SUBSCRIPT context."""

    def test_subscript_context_returns_value(self):
        """SUBSCRIPT context returns resolved value for use as subscript."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"B": "2"})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve("B", levels=1, context=IndirectionContext.SUBSCRIPT)
        assert result == "2"


class TestInvalidLevels:
    """Tests for invalid level values."""

    def test_zero_levels_raises(self):
        """levels=0 raises ValueError."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "Y"})
        resolver = IndirectionResolver(state, scope)

        with pytest.raises(ValueError):
            resolver.resolve("X", levels=0)

    def test_negative_levels_raises(self):
        """Negative levels raises ValueError."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "Y"})
        resolver = IndirectionResolver(state, scope)

        with pytest.raises(ValueError):
            resolver.resolve("X", levels=-1)


class TestMugjPatterns:
    """Tests based on MUGJ test patterns."""

    def test_v1idnm2_basic(self):
        """V1IDNM2 I-497: S A="B",@A=1 sets B=1."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"A": "B", "B": 0})
        resolver = IndirectionResolver(state, scope)

        # @A resolves to "B", which is a valid var name
        # So this returns the VALUE of B
        var_name = resolver.resolve("A", levels=1, context=IndirectionContext.NAME)
        assert var_name == 0  # Current value of B

    def test_v1idarg1_challenge_6(self):
        """V1IDARG1 I-417: S A="1=0" I @A → FALSE."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"A": "1=0"})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve("A", levels=1, context=IndirectionContext.ARGUMENT)
        assert result == 0  # FALSE


class TestHelperMethods:
    """Tests for internal helper methods."""

    def test_is_valid_var_name_local(self):
        """Local variable names are valid."""
        state = MockMState()
        scope = CurrentScope(scope_dict={})
        resolver = IndirectionResolver(state, scope)

        assert resolver._is_valid_var_name("X")
        assert resolver._is_valid_var_name("ABC")
        assert resolver._is_valid_var_name("TEST123")
        assert resolver._is_valid_var_name("%ZU")

    def test_is_valid_var_name_global(self):
        """Global variable names are valid."""
        state = MockMState()
        scope = CurrentScope(scope_dict={})
        resolver = IndirectionResolver(state, scope)

        assert resolver._is_valid_var_name("^GLO")
        assert resolver._is_valid_var_name("^TEST")
        assert resolver._is_valid_var_name("^%ZG")

    def test_is_valid_var_name_naked(self):
        """Naked reference is valid."""
        state = MockMState()
        scope = CurrentScope(scope_dict={})
        resolver = IndirectionResolver(state, scope)

        assert resolver._is_valid_var_name("^")
        assert resolver._is_valid_var_name("^(1)")

    def test_is_valid_var_name_invalid(self):
        """Invalid variable names."""
        state = MockMState()
        scope = CurrentScope(scope_dict={})
        resolver = IndirectionResolver(state, scope)

        assert not resolver._is_valid_var_name("")
        assert not resolver._is_valid_var_name("123")
        assert not resolver._is_valid_var_name("1+1")
        # Note: "X>5" starts with a valid var name char, so basic check passes.
        # The full expression validation happens in resolve() when context=NAME.

    def test_parse_subscripted_name(self):
        """Parse subscripted names correctly."""
        state = MockMState()
        scope = CurrentScope(scope_dict={})
        resolver = IndirectionResolver(state, scope)

        base, subs = resolver._parse_subscripted_name("A(1,2)")
        assert base == "A"
        assert subs == ["1", "2"]

        base, subs = resolver._parse_subscripted_name("^GLO(x,y)")
        assert base == "^GLO"
        assert subs == ["x", "y"]

        base, subs = resolver._parse_subscripted_name("X")
        assert base == "X"
        assert subs == []

    def test_append_subscripts(self):
        """Append subscripts to names."""
        state = MockMState()
        scope = CurrentScope(scope_dict={})
        resolver = IndirectionResolver(state, scope)

        # No existing subscripts
        result = resolver._append_subscripts("A", [1, 2])
        assert result == "A(1,2)"

        # Existing subscripts
        result = resolver._append_subscripts("A(1)", [2, 3])
        assert result == "A(1,2,3)"

        # Empty subscripts
        result = resolver._append_subscripts("A", [])
        assert result == "A"


class TestResolveToName:
    """Tests for resolve_to_name() for SET operations.

    resolve_to_name() returns the TARGET VARIABLE NAME for SET,
    not the value at that location.
    """

    def test_single_level_returns_name(self):
        """@X where X="Y" → "Y" (the name to SET)."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "Y", "Y": 5})
        resolver = IndirectionResolver(state, scope)

        target = resolver.resolve_to_name("X", levels=1)
        assert target == "Y"

    def test_two_level_returns_final_name(self):
        """@@X where X="Y", Y="Z" → "Z" (the name to SET)."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "Y", "Y": "Z", "Z": 99})
        resolver = IndirectionResolver(state, scope)

        target = resolver.resolve_to_name("X", levels=2)
        assert target == "Z"

    def test_three_level_returns_final_name(self):
        """@@@X where X→Y→Z→W → "W" (the name to SET)."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "Y", "Y": "Z", "Z": "W", "W": 42})
        resolver = IndirectionResolver(state, scope)

        target = resolver.resolve_to_name("X", levels=3)
        assert target == "W"

    def test_with_per_level_subscripts(self):
        """@X@(1,2) where X="A" → "A(1,2)" (the name to SET)."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "A"})
        resolver = IndirectionResolver(state, scope)

        target = resolver.resolve_to_name("X", levels=1, per_level_subscripts=[[1, 2]])
        assert target == "A(1,2)"

    def test_two_level_with_subscripts(self):
        """@@X@(1)@(2) where X="A", A(1)="B" → "B(2)" (the name to SET)."""
        state = MockMState()
        from m2py.runtime import MArray

        A = MArray()
        A[1].value = "B"
        scope = CurrentScope(scope_dict={"X": "A", "A": A, "B": 0})
        resolver = IndirectionResolver(state, scope)

        target = resolver.resolve_to_name(
            "X", levels=2, per_level_subscripts=[[1], [2]]
        )
        assert target == "B(2)"

    def test_invalid_name_raises_varexpected(self):
        """resolve_to_name raises VarExpectedError for invalid names."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "1+1"})
        resolver = IndirectionResolver(state, scope)

        with pytest.raises(VarExpectedError):
            resolver.resolve_to_name("X", levels=1)

    def test_empty_name_raises_varexpected(self):
        """resolve_to_name raises VarExpectedError for empty names."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": ""})
        resolver = IndirectionResolver(state, scope)

        with pytest.raises(VarExpectedError):
            resolver.resolve_to_name("X", levels=1)

    def test_numeric_name_raises_varexpected(self):
        """resolve_to_name raises VarExpectedError for numeric names."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "123"})
        resolver = IndirectionResolver(state, scope)

        with pytest.raises(VarExpectedError):
            resolver.resolve_to_name("X", levels=1)

    def test_global_name_is_valid(self):
        """resolve_to_name handles global variable names."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "^GLO"})
        resolver = IndirectionResolver(state, scope)

        target = resolver.resolve_to_name("X", levels=1)
        assert target == "^GLO"

    def test_global_name_with_subscripts(self):
        """@X@(1) where X="^GLO" → "^GLO(1)"."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "^GLO"})
        resolver = IndirectionResolver(state, scope)

        target = resolver.resolve_to_name("X", levels=1, per_level_subscripts=[[1]])
        assert target == "^GLO(1)"

    def test_percent_name_is_valid(self):
        """resolve_to_name handles percent-prefixed names."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "%ZX"})
        resolver = IndirectionResolver(state, scope)

        target = resolver.resolve_to_name("X", levels=1)
        assert target == "%ZX"
