"""Unit tests for subscript-level indirection.

Tests the ability to use @VAR within subscript positions like A(1,@B,3).

Feature: 018-unified-variable-system
Requirements: FR-018 (Subscript Indirection)
Tasks: T036c, T036d
"""

import pytest

from m2py.core.indirection import IndirectionResolver, IndirectionContext
from m2py.core.scope import CurrentScope


class MockMState:
    """Mock MState for testing."""

    def __init__(self):
        self._globals = MockGlobalStorage()

    def execute_mumps(self, code: str, scope: dict) -> None:
        """Mock execute_mumps that handles simple expressions."""
        if code.startswith("S "):
            rest = code[2:]
            eq_pos = rest.find("=")
            if eq_pos > 0:
                var_name = rest[:eq_pos].strip()
                expr = rest[eq_pos + 1 :].strip()
                try:
                    if "." in expr:
                        scope[var_name] = float(expr)
                    else:
                        scope[var_name] = int(expr)
                except ValueError:
                    if expr.startswith('"') and expr.endswith('"'):
                        scope[var_name] = expr[1:-1]
                    else:
                        scope[var_name] = scope.get(expr, "")

    def get_var(self, name: str, scope: dict):
        """Mock get_var."""
        return scope.get(name, "")


class MockGlobalStorage:
    """Mock global storage."""

    def __init__(self):
        self._data = {}

    def get(self, key: str, subscripts: tuple = ()):
        full_key = (key, subscripts)
        return self._data.get(full_key)


class TestSubscriptIndirection:
    """Tests for subscript-level indirection A(1,@B,3)."""

    def test_resolve_subscript_indirection_simple(self):
        """Basic subscript indirection: @B within subscript resolves to value."""
        scope_dict = {"B": "2"}
        scope = CurrentScope(scope_dict=scope_dict)
        state = MockMState()
        resolver = IndirectionResolver(state, scope)

        # S B=2, then @B in subscript position should resolve to 2
        result = resolver.resolve_subscript_indirection("B")
        assert result == "2"

    def test_resolve_subscript_indirection_numeric(self):
        """Subscript indirection with numeric value returns the value."""
        scope_dict = {"IDX": 5}
        scope = CurrentScope(scope_dict=scope_dict)
        state = MockMState()
        resolver = IndirectionResolver(state, scope)

        result = resolver.resolve_subscript_indirection("IDX")
        # Returns the value as stored (integer), which gets converted
        # to string during subscript canonicalization when used
        assert result == 5


class TestSubscriptIndirectionContext:
    """Tests for SUBSCRIPT context in resolve() method.

    Feature: 018-unified-variable-system

    Note: For typical subscript indirection A(1,@B,3), use resolve_subscript_indirection()
    instead of resolve() with SUBSCRIPT context.

    The resolve() with SUBSCRIPT context follows the standard multi-level resolution.
    If the final resolved value is a valid MUMPS variable name, it looks up that
    variable and returns its value. If not a valid name, returns the value as-is.
    """

    def test_subscript_context_returns_variable_name_string(self):
        """SUBSCRIPT context in resolve() looks up the resolved name as a variable.

        Feature: 018-unified-variable-system
        When the resolved value is a valid MUMPS variable name, SUBSCRIPT context
        looks it up and returns the variable's value.
        Per Spec 021, if undefined, LVUNDEF is raised.
        """
        from m2py.core.exceptions import LVUNDEFError

        scope_dict = {"VAR": "TARGET"}  # VAR contains valid MUMPS name "TARGET"
        scope = CurrentScope(scope_dict=scope_dict)
        state = MockMState()
        resolver = IndirectionResolver(state, scope)

        # resolve() with SUBSCRIPT context: VAR contains "TARGET",
        # so we resolve VAR → "TARGET", then since "TARGET" is a valid
        # var name, we try to look it up - which raises LVUNDEF since undefined
        with pytest.raises(LVUNDEFError):
            resolver.resolve("VAR", 1, context=IndirectionContext.SUBSCRIPT)

    def test_subscript_context_invalid_varname_returns_as_is(self):
        """SUBSCRIPT context returns non-variable-name values as-is.

        Feature: 018-unified-variable-system
        When the resolved value is NOT a valid MUMPS variable name (e.g., contains
        underscores, special characters, or is numeric), it's returned as-is for
        use as a subscript value.
        """
        scope_dict = {"VAR": "test_value"}  # Contains underscore - invalid MUMPS name
        scope = CurrentScope(scope_dict=scope_dict)
        state = MockMState()
        resolver = IndirectionResolver(state, scope)

        # resolve() with SUBSCRIPT context: VAR contains "test_value",
        # which is NOT a valid MUMPS variable name (underscores not allowed),
        # so it's returned as-is to be used as the subscript value
        result = resolver.resolve("VAR", 1, context=IndirectionContext.SUBSCRIPT)
        assert result == "test_value"

    def test_subscript_indirection_vs_name_indirection(self):
        """Demonstrate difference between subscript and name indirection."""
        # With NAME context, @VAR where VAR="X", X=5 returns 5
        # With resolve_subscript_indirection, @VAR returns the VALUE of VAR directly
        scope_dict = {"VAR": "X", "X": 5}
        scope = CurrentScope(scope_dict=scope_dict)
        state = MockMState()
        resolver = IndirectionResolver(state, scope)

        # resolve_subscript_indirection just gets VAR's value = "X"
        subscript_result = resolver.resolve_subscript_indirection("VAR")
        assert subscript_result == "X"

        # NAME context resolves @VAR → "X" → 5
        name_result = resolver.resolve("VAR", 1, context=IndirectionContext.NAME)
        assert name_result == 5

    def test_subscript_indirection_gets_direct_value(self):
        """resolve_subscript_indirection returns the variable's direct value."""
        scope_dict = {"IDX": 42, "NAME": "hello"}
        scope = CurrentScope(scope_dict=scope_dict)
        state = MockMState()
        resolver = IndirectionResolver(state, scope)

        # @IDX in subscript position gives value 42
        assert resolver.resolve_subscript_indirection("IDX") == 42
        # @NAME in subscript position gives value "hello"
        assert resolver.resolve_subscript_indirection("NAME") == "hello"


class TestV1IDNM2SubscriptPatterns:
    """Tests matching V1IDNM2 patterns for subscript indirection.

    Pattern: S B=2 W A(1,@B,3) - accessing A(1,2,3) via subscript indirection.
    """

    def test_i507_style_subscript_indirection(self):
        """V1IDNM2-I507 style: subscript indirection with integer value.

        Original MUMPS:
            S B=2
            S A(1,2,3)="target"
            W A(1,@B,3)  ; Should output "target"
        """
        from m2py.runtime import MArray

        # Setup: A(1,2,3)="target", B=2
        A = MArray()
        A["1"]["2"]["3"] = "target"
        scope_dict = {"A": A, "B": 2}
        scope = CurrentScope(scope_dict=scope_dict)
        state = MockMState()
        resolver = IndirectionResolver(state, scope)

        # Resolve the subscript indirections individually
        resolved_subs = ["1", resolver.resolve_subscript_indirection("B"), "3"]

        # Access A with resolved subscripts
        assert resolved_subs == ["1", 2, "3"]

        # The actual access would be A(1,2,3)
        result = scope.get_subscripted("A", resolved_subs)
        assert result == "target"

    def test_subscript_indirection_with_string_value(self):
        """Subscript indirection where indirected value is a string key.

        Original MUMPS:
            S KEY="alpha"
            S DATA("alpha")="found"
            W DATA(@KEY)  ; Should output "found"
        """
        from m2py.runtime import MArray

        DATA = MArray()
        DATA["alpha"] = "found"
        scope_dict = {"DATA": DATA, "KEY": "alpha"}
        scope = CurrentScope(scope_dict=scope_dict)
        state = MockMState()
        resolver = IndirectionResolver(state, scope)

        # Resolve @KEY to "alpha"
        resolved_subs = [resolver.resolve_subscript_indirection("KEY")]
        assert resolved_subs == ["alpha"]

        # Access DATA("alpha")
        result = scope.get_subscripted("DATA", resolved_subs)
        assert result == "found"

    def test_multiple_subscript_indirections(self):
        """Multiple levels of subscript indirection in same reference.

        Original MUMPS:
            S X=1, Y=2, Z=3
            S A(1,2,3)="deep"
            W A(@X,@Y,@Z)  ; Should output "deep"
        """
        from m2py.runtime import MArray

        A = MArray()
        A["1"]["2"]["3"] = "deep"
        scope_dict = {"A": A, "X": 1, "Y": 2, "Z": 3}
        scope = CurrentScope(scope_dict=scope_dict)
        state = MockMState()
        resolver = IndirectionResolver(state, scope)

        subscripts = ["@X", "@Y", "@Z"]
        resolved_subs = [
            resolver.resolve_subscript_indirection(s[1:]) if s.startswith("@") else s
            for s in subscripts
        ]
        assert resolved_subs == [1, 2, 3]

        result = scope.get_subscripted("A", resolved_subs)
        assert result == "deep"
