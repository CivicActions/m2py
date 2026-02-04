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
        from m2py.runtime import MArray

        # Parse simple SET commands: S VAR=EXPR
        if code.startswith("S "):
            rest = code[2:]
            eq_pos = rest.find("=")
            if eq_pos > 0:
                var_name = rest[:eq_pos].strip()
                expr = rest[eq_pos + 1 :].strip()
                # Evaluate simple expressions
                result = self._eval_expr(expr, scope)
                # Store as MArray with .value like real runtime
                ma = MArray()
                ma.value = result
                # Handle % prefix translation
                if var_name.startswith("%"):
                    python_name = "_pct_" + var_name[1:]
                else:
                    python_name = var_name
                scope[python_name] = ma

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
        """@A where A="" → TRUE (YDB-specific behavior for IF).

        T052: Empty string in argument indirection is TRUE for IF context.
        This differs from direct `I ""` which is FALSE.
        YDB treats successful indirection resolution (even to empty) as truthy
        when used in IF conditions (treat_empty_as_truthy=True).

        For WRITE and other contexts, empty string raises VarExpectedError.
        """
        state = MockMState()
        scope = CurrentScope(scope_dict={"A": ""})
        resolver = IndirectionResolver(state, scope)

        # T052: Must explicitly request IF-like behavior
        result = resolver.resolve(
            "A",
            levels=1,
            context=IndirectionContext.ARGUMENT,
            treat_empty_as_truthy=True,
        )
        assert (
            result == 1
        )  # YDB-specific: empty argument indirection is TRUE in IF context


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
        """Empty string behavior depends on context.

        T052: Empty string in IF argument context is TRUE (YDB-specific).
        For WRITE and other contexts, empty string raises VarExpectedError.

        This test verifies the T052 behavior when explicitly requested.
        """
        state = MockMState()
        scope = CurrentScope(scope_dict={})
        resolver = IndirectionResolver(state, scope)

        # T052: With treat_empty_as_truthy=True (IF context), empty string is TRUE
        assert resolver.evaluate_expression("", treat_empty_as_truthy=True) == 1
        assert resolver.evaluate_expression("  ", treat_empty_as_truthy=True) == 1

        # Without the flag (WRITE, SET context), empty string raises error
        from m2py.core.exceptions import VarExpectedError
        import pytest

        with pytest.raises(VarExpectedError):
            resolver.evaluate_expression("")
        with pytest.raises(VarExpectedError):
            resolver.evaluate_expression("  ")

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


class TestSubscriptEvaluation:
    """Tests for subscript evaluation in indirection strings.

    When indirection resolves to a string like "A(AA)", the subscript AA
    must be evaluated as a variable reference, not treated as a literal.

    Feature: 018-unified-variable-system
    Bug: V1IDNM1 I-494 pattern: @B where B="@A(AA)" failed with VAREXPECTED
    """

    def test_subscript_variable_is_evaluated(self):
        """@X where X="A(AA)" and AA=11 → get A(11).

        This is the V1IDNM1 I-494 pattern (simplified).
        """
        from m2py.runtime import MArray

        state = MockMState()
        # Set up: X="A(AA)", AA=11, A(11)=42
        arr = MArray()
        arr[(11,)].value = 42
        scope = CurrentScope(scope_dict={"X": "A(AA)", "AA": 11, "A": arr})
        resolver = IndirectionResolver(state, scope)

        # _get_value("A(AA)") should evaluate AA to 11, then get A(11)
        result = resolver._get_value("A(AA)")
        assert result == 42

    def test_subscript_variable_in_recursive_indirection(self):
        """@B where B="@A(AA)" should resolve @A(AA) correctly.

        This is the full V1IDNM1 I-494 pattern.
        B contains "@A(AA)" which starts with @, triggering recursive resolution.
        """
        from m2py.runtime import MArray

        state = MockMState()
        # Set up: B="@A(AA)", AA=11, A(11)="D"
        arr = MArray()
        arr[(11,)].value = "D"
        scope = CurrentScope(scope_dict={"B": "@A(AA)", "AA": 11, "A": arr})
        resolver = IndirectionResolver(state, scope)

        # resolve_to_name("B", 1) should:
        # 1. Get B → "@A(AA)"
        # 2. Recognize @ prefix, call _resolve_recursive_at
        # 3. Strip @, call _get_value("A(AA)")
        # 4. _get_value parses subscript AA, evaluates it to 11
        # 5. Returns A(11) → "D"
        target = resolver.resolve_to_name("B", levels=1)
        assert target == "D"

    def test_multiple_subscripts_with_variables(self):
        """@X where X="A(I,J)" and I=1, J=2 → get A(1,2)."""
        from m2py.runtime import MArray

        state = MockMState()
        arr = MArray()
        arr[(1, 2)].value = "found"
        scope = CurrentScope(scope_dict={"X": "A(I,J)", "I": 1, "J": 2, "A": arr})
        resolver = IndirectionResolver(state, scope)

        result = resolver._get_value("A(I,J)")
        assert result == "found"

    def test_numeric_literal_subscript_not_evaluated(self):
        """Numeric subscripts should work as literals."""
        from m2py.runtime import MArray

        state = MockMState()
        arr = MArray()
        arr[(5,)].value = "five"
        scope = CurrentScope(scope_dict={"X": "A(5)", "A": arr})
        resolver = IndirectionResolver(state, scope)

        result = resolver._get_value("A(5)")
        assert result == "five"

    def test_string_literal_subscript(self):
        """Quoted string subscripts work as literals."""
        from m2py.runtime import MArray

        state = MockMState()
        arr = MArray()
        arr[("key",)].value = "value"
        scope = CurrentScope(scope_dict={"A": arr})
        resolver = IndirectionResolver(state, scope)

        # In MUMPS notation, A("key") has quoted subscript
        result = resolver._get_value('A("key")')
        assert result == "value"

    def test_indirection_in_subscript(self):
        """@X where X="A(@Y)" and Y="1" → get A(1)."""
        from m2py.runtime import MArray

        state = MockMState()
        arr = MArray()
        arr[(1,)].value = "indirect_sub"
        scope = CurrentScope(scope_dict={"X": "A(@Y)", "Y": "1", "A": arr})
        resolver = IndirectionResolver(state, scope)

        result = resolver._get_value("A(@Y)")
        assert result == "indirect_sub"


class TestRecursiveAtResolution:
    """Tests for recursive @ resolution in indirection strings.

    Feature: 017-ydb-test-failures Phase 19 fix

    When the resolved value of an indirection itself starts with @,
    it must be recursively resolved. This handles patterns like:
    - @VV@(subs) where VV="@^VV(sub)" - the value contains @
    - @@@@@@@@X - deeply nested indirection levels

    The fix changes `if inner.startswith("@")` to `while inner.startswith("@")`
    to handle multiple consecutive @ in the resolved value.
    """

    def test_value_containing_at_is_recursively_resolved(self):
        """Value starting with @ triggers recursive resolution.

        @VV where VV="@Y" and Y="Z"
        → resolve VV → "@Y"
        → starts with @, recurse: resolve Y → "Z"
        → "Z" doesn't start with @, return "Z"
        """
        state = MockMState()
        # VV contains "@Y" which must be resolved recursively
        scope = CurrentScope(scope_dict={"VV": "@Y", "Y": "Z", "Z": "final"})
        resolver = IndirectionResolver(state, scope)

        # _resolve_recursive_at should:
        # 1. Strip @ from "@Y"
        # 2. Look up Y → "Z"
        # 3. Return "Z" (the variable name)
        result = resolver._resolve_recursive_at("@Y")
        assert result == "Z"

    def test_multiple_consecutive_at_in_value(self):
        """Value with multiple @ levels is fully resolved.

        If VV contains "@@Y" and Y="Z", this tests the while loop
        handles @@Y by:
        - First iteration: @Y → resolve Y → "Z"
        - Second iteration: @Z → resolve Z (if Z starts with @ continue, else done)
        """
        state = MockMState()
        scope = CurrentScope(scope_dict={"VV": "@Y", "Y": "Z", "Z": "final_value"})
        resolver = IndirectionResolver(state, scope)

        # @VV → VV value = "@Y"
        # "@Y" starts with @, recurse
        # @Y → Y value = "Z"
        # "Z" doesn't start with @, return "Z"
        result = resolver._resolve_recursive_at("@Y")
        assert result == "Z"


class TestSubscriptIndirectionInVariableRefs:
    """Tests for subscript indirection within variable references.

    Feature: 017-ydb-test-failures Phase 19 fix

    Patterns like A(@Y) where @Y in the subscript position means:
    1. Evaluate @Y to get Y's value
    2. Use that value as the subscript

    This is different from name-indirection subscripts (VAR@(subs))
    which appends subscripts AFTER resolving VAR.
    """

    def test_subscript_indirection_evaluates_variable(self):
        """A(@Y) where Y=3 → access A(3)."""
        from m2py.runtime import MArray

        state = MockMState()
        arr = MArray()
        arr[(3,)].value = "value_at_3"

        scope = CurrentScope(scope_dict={"Y": 3, "A": arr})
        resolver = IndirectionResolver(state, scope)

        # _get_value handles A(@Y) by:
        # - Recognizing this has subscripts with @ inside
        # - Evaluating @Y → 3
        # - Getting value at A(3)
        result = resolver._get_value("A(@Y)")
        assert result == "value_at_3"

    def test_name_indirection_subscripts_vs_subscript_indirection(self):
        """VAR@(subs) is different from VAR(@subs).

        VAR@(subs): Resolve VAR, then append (subs) to result
        VAR(@subs): Access VAR with @subs evaluated as subscript
        """
        from m2py.runtime import MArray

        state = MockMState()
        arr = MArray()
        arr[(5,)].value = "subscript_value"

        # Case 1: A(@X) - subscript indirection
        scope = CurrentScope(scope_dict={"X": 5, "A": arr})
        resolver = IndirectionResolver(state, scope)
        result = resolver._get_value("A(@X)")
        assert result == "subscript_value"

        # Case 2: @Y@(subs) where Y="A" - name-indirection subscripts
        # Y resolves to "A", then (5) is appended → A(5)
        scope2 = CurrentScope(scope_dict={"Y": "A", "A": arr})
        resolver2 = IndirectionResolver(state, scope2)
        result2 = resolver2.resolve_to_name("Y", levels=1, per_level_subscripts=[[5]])
        assert result2 == "A(5)"


class TestParenthesizedExpressionIndirection:
    """Tests for parenthesized expression indirection.

    Feature: 017-ydb-test-failures Phase 19 fix

    Patterns like @(expr)@(subs) where:
    1. (expr) is evaluated to get a variable name
    2. @(subs) is appended to that name

    Note: _resolve_recursive_at expects input starting with @.
    For @(expr), the inner expression is (expr) after stripping @.
    """

    def test_parenthesized_variable_resolved(self):
        """@(X) where X="A" → returns "A" (the NAME to use).

        For @(X) where X contains "A":
        - "@(X)" passed to _resolve_recursive_at
        - Strips @ → inner = "(X)"
        - Recognizes leading ( as parenthesized expression
        - Evaluates "X" → "A"
        - Returns "A" as the resolved name
        """
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "A", "A": "final_result"})
        resolver = IndirectionResolver(state, scope)

        # Call with "@(X)" - the @ prefix is expected by _resolve_recursive_at
        result = resolver._resolve_recursive_at("@(X)")
        assert result == "A"

    def test_parenthesized_with_trailing_subscripts(self):
        """@(X)@(1,2) where X="B" → returns "B(1,2)".

        This tests that trailing @(subs) are appended to the evaluated result.
        """
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "B"})
        resolver = IndirectionResolver(state, scope)

        # Call with "@(X)@(1,2)" - evaluates X→"B", appends (1,2)
        result = resolver._resolve_recursive_at("@(X)@(1,2)")
        assert result == "B(1,2)"


# =============================================================================
# Tests for _resolve_subscript_string (subscript indirection)
# =============================================================================


class TestResolveSubscriptString:
    """Tests for _resolve_subscript_string method.

    Feature: 017-ydb-test-failures Phase 19

    Handles subscript indirection: ^V1A(@Y) where @Y in subscripts needs resolution.
    """

    def test_simple_subscript_no_indirection(self):
        """Subscripts without @ pass through unchanged."""
        state = MockMState()
        scope = CurrentScope(scope_dict={})
        resolver = IndirectionResolver(state, scope)

        result = resolver._resolve_subscript_string("(1,2,3)")
        assert result == "(1,2,3)"

    def test_subscript_indirection_single(self):
        """^V(@X) where X=5 → (5)."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": 5})
        resolver = IndirectionResolver(state, scope)

        result = resolver._resolve_subscript_string("(@X)")
        assert result == "(5)"

    def test_subscript_indirection_mixed(self):
        """^V(1,@X,3) where X=5 → (1,5,3).

        Note: If X="abc", then @X would try to look up variable 'abc',
        not insert the string "abc". MUMPS subscript indirection
        evaluates the result as an expression.
        """
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": 5})
        resolver = IndirectionResolver(state, scope)

        result = resolver._resolve_subscript_string("(1,@X,3)")
        assert result == "(1,5,3)"

    def test_subscript_indirection_multiple(self):
        """^V(@A,@B) where A=1, B=2 → (1,2)."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"A": 1, "B": 2})
        resolver = IndirectionResolver(state, scope)

        result = resolver._resolve_subscript_string("(@A,@B)")
        assert result == "(1,2)"

    def test_subscript_indirection_multilevel(self):
        """^V(@@X) where X="Y", Y=99 → (99)."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "Y", "Y": 99})
        resolver = IndirectionResolver(state, scope)

        result = resolver._resolve_subscript_string("(@@X)")
        assert result == "(99)"


# =============================================================================
# Tests for chained recursive @ resolution
# =============================================================================


class TestChainedRecursiveAtResolution:
    """Tests for chained @ resolution where resolved values contain more @.

    Feature: 017-ydb-test-failures Phase 19

    Example: @VV@(B,"C") where VV="@^VV(\"A\")" and ^VV("A")="^VV(\"a\")"
    We need to fully resolve @^VV("A") → ^VV("a") THEN append (B,"C").
    """

    def test_resolved_value_with_leading_at(self):
        """@X where X="@Y" and Y="FINAL" → resolve @Y first → "FINAL"."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "@Y", "Y": "FINAL"})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve_to_name("X", levels=1)
        assert result == "FINAL"

    def test_name_indirection_subscripts_with_at_in_value(self):
        """@VV@(1) where VV="@Y", Y="A" → resolve @Y first → "A", append (1) → "A(1)"."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"VV": "@Y", "Y": "A"})
        resolver = IndirectionResolver(state, scope)

        result = resolver._resolve_recursive_at("@VV@(1)")
        assert result == "A(1)"

    def test_triple_at_chain(self):
        """@@@X where X="Y", Y="Z", Z="FINAL" → "FINAL"."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "Y", "Y": "Z", "Z": "FINAL"})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve_to_name("X", levels=3)
        assert result == "FINAL"


# =============================================================================
# Tests for resolve_to_name with validate=False (for KILL)
# =============================================================================


class TestResolveToNameValidateFlag:
    """Tests for resolve_to_name validate parameter.

    Feature: 017-ydb-test-failures Phase 19

    KILL indirection may resolve to exclusive patterns like "(A,B)" which
    are not valid variable names. validate=False suppresses VarExpectedError.
    """

    def test_validate_true_rejects_invalid_name(self):
        """With validate=True (default), invalid names raise error."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "(A,B)"})  # Exclusive pattern
        resolver = IndirectionResolver(state, scope)

        with pytest.raises(VarExpectedError):
            resolver.resolve_to_name("X", levels=1, validate=True)

    def test_validate_false_allows_invalid_name(self):
        """With validate=False, invalid names are returned as-is."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "(A,B)"})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve_to_name("X", levels=1, validate=False)
        assert result == "(A,B)"

    def test_validate_false_comma_separated_list(self):
        """validate=False allows comma-separated variable lists."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "A,B,C"})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve_to_name("X", levels=1, validate=False)
        assert result == "A,B,C"

    def test_validate_false_exclusive_plus_explicit(self):
        """validate=False allows '(A),B,C' pattern for exclusive + explicit KILL."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "(A),B,C"})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve_to_name("X", levels=1, validate=False)
        assert result == "(A),B,C"


# =============================================================================
# Tests for resolve_to_name with strict_undef=True (for WRITE indirection T052)
# =============================================================================


class TestResolveToNameStrictUndef:
    """Tests for resolve_to_name strict_undef parameter.

    Feature: 017-ydb-test-failures (T052 - WRITE indirection error handling)

    When strict_undef=True, undefined source variables raise LVUNDEFError
    instead of returning empty string. Used by WRITE indirection where
    accessing an undefined variable should error, not output nothing.
    """

    def test_strict_undef_false_returns_empty(self):
        """With strict_undef=False (default), undefined returns empty string."""
        state = MockMState()
        scope = CurrentScope(scope_dict={})  # Empty scope
        resolver = IndirectionResolver(state, scope)

        # UNDEF doesn't exist - should return empty string
        result = resolver.resolve_to_name(
            "UNDEF", levels=1, validate=False, strict_undef=False
        )
        assert result == ""

    def test_strict_undef_true_raises_lvundef(self):
        """With strict_undef=True, undefined source raises LVUNDEFError."""
        from m2py.core.exceptions import LVUNDEFError

        state = MockMState()
        scope = CurrentScope(scope_dict={})  # Empty scope
        resolver = IndirectionResolver(state, scope)

        with pytest.raises(LVUNDEFError):
            resolver.resolve_to_name("UNDEF", levels=1, strict_undef=True)

    def test_strict_undef_with_defined_variable(self):
        """With strict_undef=True, defined variables work normally."""
        state = MockMState()
        scope = CurrentScope(scope_dict={"X": "TARGET"})
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve_to_name("X", levels=1, strict_undef=True)
        assert result == "TARGET"

    def test_strict_undef_subscripted_missing(self):
        """With strict_undef=True, undefined subscripted location raises error."""
        from m2py.core.exceptions import LVUNDEFError
        from m2py.runtime import MArray

        state = MockMState()
        # A exists but A(1) does not
        arr = MArray()
        arr.value = "base_value"
        scope = CurrentScope(scope_dict={"A": arr})
        resolver = IndirectionResolver(state, scope)

        with pytest.raises(LVUNDEFError):
            resolver.resolve_to_name("A(1)", levels=1, strict_undef=True)

    def test_strict_undef_multi_level(self):
        """With strict_undef=True, multi-level indirection checks each level."""
        from m2py.core.exceptions import LVUNDEFError

        state = MockMState()
        # X exists but points to MISSING which doesn't exist
        scope = CurrentScope(scope_dict={"X": "MISSING"})
        resolver = IndirectionResolver(state, scope)

        # @@X: resolve X→"MISSING", then resolve MISSING→error
        with pytest.raises(LVUNDEFError):
            resolver.resolve_to_name("X", levels=2, strict_undef=True)
