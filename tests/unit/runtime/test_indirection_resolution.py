"""Tests for indirection resolution methods.

Tests the runtime methods for resolving name indirection:
- resolve_nested_indirection: Recursive indirection resolution
- _evaluate_subscript: VarRef subscript evaluation
- get_indirected: Unified indirection method (IndirectionResolver)

Also includes V1IDNM1 test case fixes:
- I-491: FOR loops with indirect variables resolving to subscripted names
- I-492: Function-based indirection returning variable name instead of value
- I-494: Subscripted VarRef evaluation in get_var()

Reference: MUMPS allows complex indirection chains like @A where A="@B",
B="@$E(""XYZ"",2)" which resolves to "Y".
"""

import pytest
from m2py.runtime import (
    MArray,
    MUMPSRuntime,
    IndirectionError,
    _evaluate_subscript,
    VarRef,
)


# =============================================================================
# MUMPSRuntime.resolve_nested_indirection Tests
# =============================================================================


class TestResolveNestedIndirection:
    """Tests for resolve_nested_indirection method.

    This method recursively resolves @ prefixes until reaching
    a non-@ value.
    """

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_no_at_prefix_unchanged(self, rt):
        """Value without @ prefix is returned unchanged."""
        result = rt.resolve_nested_indirection("LABEL", {})
        assert result == "LABEL"

    def test_simple_at_resolution(self, rt):
        """@A resolves to value of A."""
        scope = {"A": MArray()}
        scope["A"].value = "RESULT"
        result = rt.resolve_nested_indirection("@A", scope)
        assert result == "RESULT"

    def test_chained_at_resolution(self, rt):
        """@A where A="@B" and B="FINAL" resolves to "FINAL"."""
        scope = {"A": MArray(), "B": MArray()}
        scope["A"].value = "@B"
        scope["B"].value = "FINAL"
        result = rt.resolve_nested_indirection("@A", scope)
        assert result == "FINAL"

    def test_triple_chain(self, rt):
        """@A → @B → @C → FINAL."""
        scope = {"A": MArray(), "B": MArray(), "C": MArray()}
        scope["A"].value = "@B"
        scope["B"].value = "@C"
        scope["C"].value = "FINAL"
        result = rt.resolve_nested_indirection("@A", scope)
        assert result == "FINAL"

    def test_subscripted_variable(self, rt):
        """@A(1) resolves subscripted variable."""
        scope = {"A": MArray()}
        scope["A"][1].value = "VALUE"
        result = rt.resolve_nested_indirection("@A(1)", scope)
        assert result == "VALUE"

    def test_subscript_with_variable_reference(self, rt):
        """@A(I) where I=1 resolves correctly."""
        scope = {"A": MArray(), "_a_I": MArray()}
        scope["A"][1].value = "RESULT"
        scope["_a_I"].value = 1
        result = rt.resolve_nested_indirection("@A(I)", scope)
        assert result == "RESULT"

    def test_undefined_in_chain_raises(self, rt):
        """Undefined variable in chain raises IndirectionError."""
        scope = {"A": MArray()}
        scope["A"].value = "@UNDEF"
        with pytest.raises(IndirectionError):
            rt.resolve_nested_indirection("@A", scope)

    def test_empty_indirection_target_raises(self, rt):
        """Empty @ target raises IndirectionError."""
        with pytest.raises(IndirectionError):
            rt.resolve_nested_indirection("@", {})

    def test_max_depth_protection(self, rt):
        """Infinite loop protection via max_depth."""
        # Create circular reference: A → @B → @A (cycle)
        scope = {"A": MArray(), "B": MArray()}
        scope["A"].value = "@B"
        scope["B"].value = "@A"
        with pytest.raises(IndirectionError) as exc_info:
            rt.resolve_nested_indirection("@A", scope, max_depth=10)
        assert "max depth" in str(exc_info.value)

    def test_global_variable_resolution(self, rt):
        """@^GLO resolves global variable."""
        rt.globals.set("GLO", (), "GLOBAL_VALUE")
        result = rt.resolve_nested_indirection("@^GLO", {})
        assert result == "GLOBAL_VALUE"

    def test_global_subscripted(self, rt):
        """@^GLO(1) resolves subscripted global."""
        rt.globals.set("GLO", ("1",), "SUB_VALUE")
        result = rt.resolve_nested_indirection("@^GLO(1)", {})
        assert result == "SUB_VALUE"


# =============================================================================
# V1IDNM1 Test Case Fixes (T075k)
# =============================================================================


class TestIndirectForLoopSubscriptedNames:
    """Tests for I-491: FOR loops with indirect variables resolving to subscripted names.

    When a FOR loop uses an indirect variable like @A(@A(2)) and the resolved
    name is "A(22)" (a subscripted name), the loop variable must be set using
    set_var() which handles subscripts, not direct scope assignment.
    """

    @pytest.fixture
    def rt(self):
        """Create a runtime instance."""
        return MUMPSRuntime()

    @pytest.fixture
    def scope_with_indirect_refs(self, rt):
        """Create scope with variables for indirect subscript resolution.

        Setup: A(2)=22 means @A(@A(2)) resolves to A(22)
        """
        scope = {}
        rt.set_var("A", 22, scope)  # A.value = 22
        rt.set_var("A(2)", 22, scope)  # A[2] = 22
        return scope

    def test_set_var_with_subscripted_name(self, rt, scope_with_indirect_refs):
        """set_var() should handle subscripted names like 'A(22)'."""
        scope = scope_with_indirect_refs

        # This simulates what the indirect FOR loop does
        rt.set_var("A(22)", 100, scope)

        # Verify the subscript was set correctly
        assert rt.get_var("A(22)", scope) == 100
        # MArray stores values wrapped - check the .value
        assert scope["A"][22].value == 100

    def test_get_var_with_subscripted_name(self, rt, scope_with_indirect_refs):
        """get_var() should retrieve values from subscripted names like 'A(22)'."""
        scope = scope_with_indirect_refs

        # Set up the subscripted variable
        rt.set_var("A(22)", 50, scope)

        # Retrieve using subscripted name string
        value = rt.get_var("A(22)", scope)
        assert value == 50

    def test_indirect_for_loop_increments(self, rt, scope_with_indirect_refs):
        """Simulate indirect FOR loop incrementing a subscripted variable.

        This simulates: F @A(@A(2))=4:1:7 where A(2)=22 so loop var is A(22)
        """
        scope = scope_with_indirect_refs
        indirect_var = "A(22)"  # Resolved from @A(@A(2))

        # Initialize loop variable (start=4)
        rt.set_var(indirect_var, 4, scope)
        assert rt.get_var(indirect_var, scope) == 4

        # Increment (step=1)
        rt.set_var(indirect_var, rt.get_var(indirect_var, scope) + 1, scope)
        assert rt.get_var(indirect_var, scope) == 5

        # Continue incrementing until > 7 (end=7)
        rt.set_var(indirect_var, rt.get_var(indirect_var, scope) + 1, scope)
        rt.set_var(indirect_var, rt.get_var(indirect_var, scope) + 1, scope)
        rt.set_var(indirect_var, rt.get_var(indirect_var, scope) + 1, scope)

        # Loop should have set final value to 8 (which exceeds end=7)
        assert rt.get_var(indirect_var, scope) == 8


class TestFunctionBasedIndirection:
    """Tests for I-492: Function-based indirection returning variable name instead of value.

    When resolve_nested_indirection() evaluates @$E("ABCDEF",4) with return_value=True,
    it should return the VALUE of the variable D (which equals 4), not just "D".
    """

    @pytest.fixture
    def rt(self):
        """Create a runtime instance."""
        return MUMPSRuntime()

    @pytest.fixture
    def scope_with_letter_vars(self, rt):
        """Create scope with variables A-F set to 1-6.

        This matches V1IDNM1 setup where $E("ABCDEF", N) returns a var name.
        """
        scope = {}
        for i, letter in enumerate("ABCDEF", start=1):
            rt.set_var(letter, i, scope)
        return scope

    def test_resolve_nested_indirection_function_returns_value(
        self, rt, scope_with_letter_vars
    ):
        """resolve_nested_indirection with return_value=True should return var value.

        $E("ABCDEF", 4) = "D", and D = 4, so @$E("ABCDEF",4) should return 4
        Note: MUMPS returns strings, so we compare string "4" not int 4
        """
        scope = scope_with_letter_vars

        # When return_value=True, we want the value of D (which is 4), not "D"
        result = rt.resolve_nested_indirection(
            '@$E("ABCDEF",4)',  # Evaluates to "D"
            scope,
            return_value=True,
        )

        # Should return "4" (string value of D), not "D" (the variable name)
        # MUMPS values are strings - 4 stored as int becomes "4" on retrieval
        assert str(result) == "4"

    def test_resolve_nested_indirection_function_returns_name_when_no_return_value(
        self, rt, scope_with_letter_vars
    ):
        """resolve_nested_indirection with return_value=False returns variable name.

        When we just want the name for assignment, it should return "D".
        """
        scope = scope_with_letter_vars

        # When return_value=False, we want the variable name for SET
        result = rt.resolve_nested_indirection(
            '@$E("ABCDEF",4)',  # Evaluates to "D"
            scope,
            return_value=False,
        )

        # Should return "D" (the variable name)
        assert result == "D"

    def test_resolve_nested_indirection_multiple_function_calls(
        self, rt, scope_with_letter_vars
    ):
        """Nested function indirection should chain correctly.

        @$E("ABCD",2) = @"B" = value of B = 2
        Note: MUMPS returns strings, so we compare string "2" not int 2
        """
        scope = scope_with_letter_vars

        result = rt.resolve_nested_indirection(
            '@$E("ABCD",2)',  # Evaluates to "B"
            scope,
            return_value=True,
        )

        assert str(result) == "2"  # String value of B


class TestEvaluateSubscriptWithVarRefs:
    """Tests for I-494: _evaluate_subscript() parsing subscripted VarRef names.

    When _evaluate_subscript receives a VarRef like VarRef("A(1)") as a subscript,
    it should recognize this as a subscripted variable reference and look up A(1)'s value.
    """

    @pytest.fixture
    def rt(self):
        """Create a runtime instance."""
        return MUMPSRuntime()

    @pytest.fixture
    def scope_with_nested_refs(self, rt):
        """Create scope with nested variable references.

        Setup: A(1)="20:10:40" - used as subscript in A(A(1))
        """
        scope = {}
        rt.set_var("A(1)", "20:10:40", scope)
        rt.set_var("A(20:10:40)", "target_value", scope)
        return scope

    def test_evaluate_subscript_non_varref_passthrough(self, rt):
        """_evaluate_subscript should pass through non-VarRef values."""
        scope = {}
        # Non-VarRef values are passed through unchanged
        assert _evaluate_subscript(42, scope) == 42
        assert _evaluate_subscript("hello", scope) == "hello"
        assert _evaluate_subscript(3.14, scope) == 3.14

    def test_evaluate_subscript_simple_varref(self, rt, scope_with_nested_refs):
        """_evaluate_subscript should look up simple VarRef variable references."""
        scope = scope_with_nested_refs

        # Set up a simple var for lookup
        rt.set_var("X", 99, scope)

        result = _evaluate_subscript(VarRef("X"), scope)
        assert result == 99

    def test_evaluate_subscript_subscripted_varref(self, rt, scope_with_nested_refs):
        """_evaluate_subscript should parse and evaluate subscripted VarRef like 'A(1)'."""
        scope = scope_with_nested_refs

        # A(1) = "20:10:40"
        result = _evaluate_subscript(VarRef("A(1)"), scope)
        assert result == "20:10:40"

    def test_get_var_with_nested_subscript_varref(self, rt, scope_with_nested_refs):
        """get_var should handle names with literal subscripts (not variable references).

        Note: When get_var receives "A(A(1))" as a string, it treats "A(1)" as a
        literal subscript key, NOT as a variable reference. Variable reference
        resolution happens via VarRef objects in generated code, not string parsing.

        For actual nested subscript evaluation (where A(1) is a variable), the
        generated code uses MArray.get() with VarRef("A(1)") which is tested
        in test_evaluate_subscript_subscripted_varref.
        """
        scope = scope_with_nested_refs

        # get_var("A(A(1))") looks for literal key "A(1)" in A's subscripts
        # which doesn't exist, so returns empty string
        result = rt.get_var("A(A(1))", scope)
        # The literal subscript "A(1)" doesn't exist as a string key
        assert result == ""

        # The actual value at subscript "20:10:40" still exists
        assert rt.get_var("A(20:10:40)", scope) == "target_value"


class TestIntegrationV1IDNM1Scenarios:
    """Integration tests for the full V1IDNM1 scenarios.

    These tests verify the complete flow as it appears in V1IDNM1.
    """

    @pytest.fixture
    def rt(self):
        """Create a runtime instance."""
        return MUMPSRuntime()

    def test_i489_indirect_var_basic(self, rt):
        """I-489: Basic indirect variable reference."""
        scope = {}
        rt.set_var("A", "B", scope)  # A contains "B"
        rt.set_var("B", 100, scope)  # B = 100

        # @A should resolve to B, and with return_value=True, return B's value
        # MUMPS returns strings, so 100 becomes "100"
        result = rt.resolve_nested_indirection("@A", scope, return_value=True)
        assert str(result) == "100"

    def test_i491_for_loop_with_indirect_subscripted_var(self, rt):
        """I-491: FOR loop with indirect variable resolving to subscript."""
        scope = {}
        # Setup: A=A, A(2)=22 → @A(@A(2)) = A(22)
        rt.set_var("A", "A", scope)
        rt.set_var("A(2)", 22, scope)

        # Resolve the indirect var name - mimics what codegen does
        inner = rt.get_var("A(2)", scope)  # = 22
        indirect_var = f"A({inner})"  # = "A(22)"

        # FOR loop simulation
        total = 0
        for val in range(4, 8):  # 4:1:7
            rt.set_var(indirect_var, val, scope)
            total += val

        # Final value should be 7 (last iteration)
        assert rt.get_var(indirect_var, scope) == 7
        assert total == 4 + 5 + 6 + 7

    def test_i492_function_indirection_with_value(self, rt):
        """I-492: Function-based indirection returns value."""
        scope = {}
        for i, letter in enumerate("ABCDEF", start=1):
            rt.set_var(letter, i, scope)

        # @$E("ABCDEF",4) with return_value=True should return "4" (string value of D)
        result = rt.resolve_nested_indirection(
            '@$E("ABCDEF",4)', scope, return_value=True
        )
        assert str(result) == "4"

    def test_i494_nested_subscript_evaluation(self, rt):
        """I-494: Nested subscript with variable reference."""
        scope = {}
        # Setup: A(1)=2, A(2)="answer"
        rt.set_var("A(1)", 2, scope)
        rt.set_var("A(2)", "answer", scope)

        # get_var("A(A(1))") = A(2) = "answer"
        result = rt.get_var("A(A(1))", scope)
        assert result == "answer"


# =============================================================================
# MUMPSRuntime.get_indirected Tests (Unified Method)
# =============================================================================


class TestGetIndirected:
    """Tests for get_indirected() unified method.

    Feature: 018-unified-variable-system (T104, T105)
    This method uses IndirectionResolver to resolve indirection
    and then retrieves the value via CurrentScope.
    """

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_single_level_simple(self, rt):
        """Single level @X where X="Y", Y=5 → returns 5."""
        scope = {"X": MArray(), "Y": MArray()}
        scope["X"].value = "Y"
        scope["Y"].value = 5
        result = rt.get_indirected("X", scope, levels=1)
        assert result == 5

    def test_double_level(self, rt):
        """Double level @@X where X="Y", Y="Z", Z=99 → returns 99."""
        scope = {"X": MArray(), "Y": MArray(), "Z": MArray()}
        scope["X"].value = "Y"
        scope["Y"].value = "Z"
        scope["Z"].value = 99
        result = rt.get_indirected("X", scope, levels=2)
        assert result == 99

    def test_triple_level(self, rt):
        """Triple level @@@X where X="Y", Y="Z", Z="W", W=42 → returns 42."""
        scope = {"X": MArray(), "Y": MArray(), "Z": MArray(), "W": MArray()}
        scope["X"].value = "Y"
        scope["Y"].value = "Z"
        scope["Z"].value = "W"
        scope["W"].value = 42
        result = rt.get_indirected("X", scope, levels=3)
        assert result == 42

    def test_with_per_level_subscripts(self, rt):
        """@X@(1,2) where X="A", A(1,2)="hello" → returns "hello"."""
        scope = {"X": MArray(), "A": MArray()}
        scope["X"].value = "A"
        scope["A"][1, 2].value = "hello"
        result = rt.get_indirected("X", scope, levels=1, per_level_subscripts=[[1, 2]])
        assert result == "hello"

    def test_with_multiple_per_level_subscripts(self, rt):
        """@@X@(1)@(2) where X="Y", Y="Z", Z(1)(2)... → tests multi-level."""
        scope = {"X": MArray(), "Y": MArray(), "Z": MArray()}
        scope["X"].value = "Y"
        scope["Y"].value = "Z"
        # First level: Y@(1) → Y(1) not valid. Let's use simpler test
        # Actually Y@(1) appends to Y, so Y(1) as next name
        scope["X"].value = "A"
        scope["A"] = MArray()
        scope["A"][1].value = "B"  # A(1)="B"
        scope["B"] = MArray()
        scope["B"][2].value = "result"  # B(2)="result"

        # @X@(1) where X="A" → A(1) → "B"
        # @@X@(1)@(2) where X="A" → A(1)="B" → B(2)="result"
        result = rt.get_indirected(
            "X", scope, levels=2, per_level_subscripts=[[1], [2]]
        )
        assert result == "result"

    def test_undefined_raises_error(self, rt):
        """Undefined target variable raises IndirectionError (MUMPS UNDEF)."""
        from m2py.runtime import IndirectionError

        scope = {"X": MArray()}
        scope["X"].value = "UNDEFINED"
        with pytest.raises(IndirectionError):
            rt.get_indirected("X", scope, levels=1)

    def test_global_variable(self, rt):
        """@X where X="^GLO", ^GLO=42 → returns 42."""
        scope = {"X": MArray()}
        scope["X"].value = "^GLO"
        rt.globals.set("GLO", (), "42")
        result = rt.get_indirected("X", scope, levels=1)
        assert result == "42"

    def test_global_subscripted(self, rt):
        """@X@(1,2) where X="^GLO", ^GLO(1,2)="hello" → returns "hello"."""
        scope = {"X": MArray()}
        scope["X"].value = "^GLO"
        rt.globals.set("GLO", ("1", "2"), "hello")
        result = rt.get_indirected("X", scope, levels=1, per_level_subscripts=[[1, 2]])
        assert result == "hello"

    def test_percent_variable(self, rt):
        """@X where X="%Z", %Z=123 → returns 123."""
        scope = {"X": MArray(), "_pct_Z": MArray()}
        scope["X"].value = "%Z"
        scope["_pct_Z"].value = 123
        result = rt.get_indirected("X", scope, levels=1)
        assert result == 123

    def test_innermost_subscripts(self, rt):
        """@X where X="A(1)", A(1)=99 → returns 99."""
        scope = {"X": MArray(), "A": MArray()}
        scope["X"].value = "A(1)"
        scope["A"][1].value = 99
        result = rt.get_indirected("X", scope, levels=1)
        assert result == 99
