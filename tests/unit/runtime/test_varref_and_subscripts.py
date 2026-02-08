"""Tests for SubscriptVarRef class and subscript evaluation functions.

Tests the SubscriptVarRef wrapper class (aliased as VarRef for backward compatibility)
and _evaluate_subscript(s) functions that enable runtime variable reference
resolution in subscripts.

Reference: MUMPS allows variable references in subscripts like @A(I)
where I is a variable that needs to be looked up at runtime.

Note: SubscriptVarRef is distinct from core.scope.VarRef which represents
a complete variable reference for codegen/runtime unified access patterns.
"""

import pytest
from m2py.runtime import MArray, MUMPSRuntime
from m2py.runtime import (
    VarRef,  # Backward compatibility alias for SubscriptVarRef
    SubscriptVarRef,
    _evaluate_subscript,
    _evaluate_subscripts,
    _convert_subscript,
    _parse_subscripted_name,
    _split_argument_list,  # T088: Argument list parsing
    IndirectionError,
)


# =============================================================================
# SubscriptVarRef Class Tests
# =============================================================================


class TestVarRef:
    """Tests for the SubscriptVarRef wrapper class (accessed via VarRef alias)."""

    def test_varref_creation(self):
        """SubscriptVarRef stores variable name."""
        ref = VarRef("X")
        assert ref.name == "X"

    def test_varref_repr(self):
        """SubscriptVarRef has readable repr."""
        ref = VarRef("MYVAR")
        assert repr(ref) == "SubscriptVarRef('MYVAR')"

    def test_varref_different_names(self):
        """SubscriptVarRef preserves different variable names."""
        ref1 = VarRef("A")
        ref2 = VarRef("B")
        assert ref1.name == "A"
        assert ref2.name == "B"

    def test_varref_empty_name(self):
        """SubscriptVarRef accepts empty name (edge case)."""
        ref = VarRef("")
        assert ref.name == ""

    def test_alias_is_same_class(self):
        """VarRef alias refers to SubscriptVarRef class."""
        assert VarRef is SubscriptVarRef


# =============================================================================
# _convert_subscript Tests
# =============================================================================


class TestConvertSubscript:
    """Tests for _convert_subscript function."""

    def test_convert_integer(self):
        """Integer string converts to int."""
        assert _convert_subscript("42", "test") == 42

    def test_convert_negative_integer(self):
        """Negative integer converts correctly."""
        assert _convert_subscript("-5", "test") == -5

    def test_convert_float(self):
        """Float string converts to float."""
        assert _convert_subscript("3.14", "test") == 3.14

    def test_convert_negative_float(self):
        """Negative float converts correctly."""
        assert _convert_subscript("-2.5", "test") == -2.5

    def test_convert_quoted_string_double(self):
        """Double-quoted string returns unquoted value."""
        assert _convert_subscript('"hello"', "test") == "hello"

    def test_convert_quoted_string_single(self):
        """Single-quoted string returns unquoted value."""
        assert _convert_subscript("'world'", "test") == "world"

    def test_convert_unquoted_becomes_varref(self):
        """Unquoted non-numeric string becomes VarRef."""
        result = _convert_subscript("I", "test")
        assert isinstance(result, VarRef)
        assert result.name == "I"

    def test_convert_variable_name_becomes_varref(self):
        """Variable name like MYVAR becomes VarRef."""
        result = _convert_subscript("MYVAR", "test")
        assert isinstance(result, VarRef)
        assert result.name == "MYVAR"

    def test_convert_empty_raises_error(self):
        """Empty subscript raises IndirectionError."""
        with pytest.raises(IndirectionError):
            _convert_subscript("", "test()")


# =============================================================================
# _evaluate_subscript Tests
# =============================================================================


class TestEvaluateSubscript:
    """Tests for _evaluate_subscript function."""

    def test_evaluate_integer_passthrough(self):
        """Integer value passes through unchanged."""
        assert _evaluate_subscript(42, {}) == 42

    def test_evaluate_float_passthrough(self):
        """Float value passes through unchanged."""
        assert _evaluate_subscript(3.14, {}) == 3.14

    def test_evaluate_string_passthrough(self):
        """String value passes through unchanged."""
        assert _evaluate_subscript("key", {}) == "key"

    def test_evaluate_varref_looks_up_value(self):
        """VarRef is resolved by looking up in scope."""
        scope = {"X": MArray()}
        scope["X"].value = 5
        ref = VarRef("X")
        assert _evaluate_subscript(ref, scope) == 5

    def test_evaluate_varref_string_value(self):
        """VarRef resolves to string value."""
        scope = {"NAME": MArray()}
        scope["NAME"].value = "hello"
        ref = VarRef("NAME")
        assert _evaluate_subscript(ref, scope) == "hello"

    def test_evaluate_varref_undefined_returns_empty(self):
        """VarRef for undefined variable returns empty string."""
        ref = VarRef("UNDEF")
        assert _evaluate_subscript(ref, {}) == ""

    def test_evaluate_varref_non_array_value(self):
        """VarRef for non-MArray value in scope."""
        scope = {"X": "direct_value"}
        ref = VarRef("X")
        assert _evaluate_subscript(ref, scope) == "direct_value"

    def test_evaluate_none_passthrough(self):
        """None passes through (edge case)."""
        assert _evaluate_subscript(None, {}) is None


# =============================================================================
# _evaluate_subscripts Tests
# =============================================================================


class TestEvaluateSubscripts:
    """Tests for _evaluate_subscripts function."""

    def test_evaluate_none_returns_none(self):
        """None input returns None."""
        assert _evaluate_subscripts(None, {}) is None

    def test_evaluate_empty_tuple_returns_empty(self):
        """Empty tuple returns empty tuple."""
        assert _evaluate_subscripts((), {}) == ()

    def test_evaluate_all_integers(self):
        """Tuple of integers passes through."""
        result = _evaluate_subscripts((1, 2, 3), {})
        assert result == (1, 2, 3)

    def test_evaluate_mixed_with_varref(self):
        """Tuple with VarRef resolves the reference."""
        scope = {"I": MArray()}
        scope["I"].value = 10
        subs = (1, VarRef("I"), 3)
        result = _evaluate_subscripts(subs, scope)
        assert result == (1, 10, 3)

    def test_evaluate_multiple_varrefs(self):
        """Multiple VarRefs all get resolved."""
        scope = {"A": MArray(), "B": MArray()}
        scope["A"].value = 5
        scope["B"].value = 7
        subs = (VarRef("A"), VarRef("B"))
        result = _evaluate_subscripts(subs, scope)
        assert result == (5, 7)

    def test_evaluate_preserves_tuple_type(self):
        """Result is a tuple, not list."""
        result = _evaluate_subscripts((1,), {})
        assert isinstance(result, tuple)


# =============================================================================
# Integration: _parse_subscripted_name + _convert_subscript
# =============================================================================


class TestSubscriptedNameParsing:
    """Integration tests for subscripted name parsing."""

    def test_parse_simple_name(self):
        """Simple variable name has no subscripts."""
        name, subs = _parse_subscripted_name("X")
        assert name == "X"
        assert subs is None

    def test_parse_numeric_subscript(self):
        """Numeric subscript is parsed correctly."""
        name, subs = _parse_subscripted_name("ARR(1)")
        assert name == "ARR"
        assert subs == (1,)

    def test_parse_multiple_subscripts(self):
        """Multiple subscripts parsed correctly."""
        name, subs = _parse_subscripted_name("ARR(1,2,3)")
        assert name == "ARR"
        assert subs == (1, 2, 3)

    def test_parse_quoted_string_subscript(self):
        """Quoted string subscript preserved."""
        name, subs = _parse_subscripted_name('ARR("key")')
        assert name == "ARR"
        assert subs == ("key",)

    def test_parse_variable_subscript_becomes_varref(self):
        """Unquoted variable name in subscript becomes VarRef."""
        name, subs = _parse_subscripted_name("ARR(I)")
        assert name == "ARR"
        assert len(subs) == 1
        assert isinstance(subs[0], VarRef)
        assert subs[0].name == "I"

    def test_parse_mixed_subscripts(self):
        """Mixed subscript types parsed correctly."""
        name, subs = _parse_subscripted_name('ARR(1,I,"key")')
        assert name == "ARR"
        assert len(subs) == 3
        assert subs[0] == 1
        assert isinstance(subs[1], VarRef)
        assert subs[1].name == "I"
        assert subs[2] == "key"

    def test_parse_global_with_subscript(self):
        """Global variable with subscript."""
        name, subs = _parse_subscripted_name("^GLO(1)")
        assert name == "^GLO"
        assert subs == (1,)

    def test_parse_malformed_missing_close_paren(self):
        """Missing closing paren raises error."""
        with pytest.raises(IndirectionError):
            _parse_subscripted_name("ARR(1,2")

    def test_parse_empty_subscript_raises_error(self):
        """Empty subscripts raise error."""
        with pytest.raises(IndirectionError):
            _parse_subscripted_name("ARR()")


# =============================================================================
# Name Indirection in Subscripts Tests
# =============================================================================


class TestSubscriptIndirectionWithRuntime:
    """Tests for name indirection (@X) in subscripts requiring runtime resolution.

    MUMPS allows @X in subscripts where X contains a variable name that
    should be resolved and its value used. For complex nested indirection
    patterns like @@H1@(@G)@("-"), we need the full MUMPSRuntime machinery.

    Reference: II-132.2 from VV2VNIB test suite demonstrates these patterns.
    """

    @pytest.fixture
    def runtime(self):
        """Create a MUMPSRuntime instance for tests."""
        return MUMPSRuntime()

    # -------------------------------------------------------------------------
    # Simple @ Indirection Tests
    # -------------------------------------------------------------------------

    def test_simple_at_indirection_value(self, runtime):
        """@X resolves to value of X when X contains a simple value.

        MUMPS: S X="A" W @X  ; writes value of A
        """
        scope = {"X": MArray(), "A": MArray()}
        scope["X"].value = "A"
        scope["A"].value = "hello"
        ref = VarRef("@X")
        result = _evaluate_subscript(ref, scope, runtime)
        assert result == "hello"

    def test_simple_at_indirection_numeric(self, runtime):
        """@X resolves numeric value correctly.

        MUMPS: S X="N" S N=42 W @X  ; writes 42
        Note: MUMPS returns values as strings in subscript context.
        """
        scope = {"X": MArray(), "N": MArray()}
        scope["X"].value = "N"
        scope["N"].value = 42
        ref = VarRef("@X")
        result = _evaluate_subscript(ref, scope, runtime)
        # MUMPS returns numeric as string in indirection resolution
        assert result == "42"

    def test_at_indirection_undefined_target(self, runtime):
        """@X where target variable is undefined returns empty string.

        MUMPS: S X="UNDEF" W @X  ; writes empty
        """
        scope = {"X": MArray()}
        scope["X"].value = "UNDEF"
        ref = VarRef("@X")
        result = _evaluate_subscript(ref, scope, runtime)
        assert result == ""

    def test_at_indirection_subscripted_target(self, runtime):
        """@X where X contains subscripted name resolves correctly.

        MUMPS: S X="A(1)" S A(1)=99 W @X  ; writes 99
        """
        scope = {"X": MArray(), "A": MArray()}
        scope["X"].value = "A(1)"
        scope["A"].set(1, value=99)
        ref = VarRef("@X")
        result = _evaluate_subscript(ref, scope, runtime)
        assert result == "99"

    def test_at_indirection_multi_subscripted_target(self, runtime):
        """@X where X contains multi-subscripted name resolves correctly.

        MUMPS: S X="A(1,2,3)" S A(1,2,3)="deep" W @X  ; writes "deep"
        """
        scope = {"X": MArray(), "A": MArray()}
        scope["X"].value = "A(1,2,3)"
        scope["A"].set(1, 2, 3, value="deep")
        ref = VarRef("@X")
        result = _evaluate_subscript(ref, scope, runtime)
        assert result == "deep"

    # -------------------------------------------------------------------------
    # Double @@ Indirection Tests
    # -------------------------------------------------------------------------

    def test_double_at_indirection(self, runtime):
        """@@X resolves two levels of indirection.

        MUMPS: S X="Y" S Y="Z" S Z="value" W @@X  ; writes "value"
        """
        scope = {"X": MArray(), "Y": MArray(), "Z": MArray()}
        scope["X"].value = "Y"
        scope["Y"].value = "Z"
        scope["Z"].value = "value"
        ref = VarRef("@@X")
        result = _evaluate_subscript(ref, scope, runtime)
        assert result == "value"

    def test_double_at_with_numeric_chain(self, runtime):
        """@@X with numeric values through the chain.

        MUMPS: S X="Y" S Y="N" S N=123 W @@X  ; writes 123
        """
        scope = {"X": MArray(), "Y": MArray(), "N": MArray()}
        scope["X"].value = "Y"
        scope["Y"].value = "N"
        scope["N"].value = 123
        ref = VarRef("@@X")
        result = _evaluate_subscript(ref, scope, runtime)
        # MUMPS returns numeric as string in indirection resolution
        assert result == "123"

    def test_double_at_with_subscripted_intermediate(self, runtime):
        """@@X where X points to subscripted variable.

        MUMPS: S X="A(1)" S A(1)="B" S B=42 W @@X  ; writes 42
        """
        scope = {"X": MArray(), "A": MArray(), "B": MArray()}
        scope["X"].value = "A(1)"
        scope["A"].set(1, value="B")
        scope["B"].value = 42
        ref = VarRef("@@X")
        result = _evaluate_subscript(ref, scope, runtime)
        # MUMPS returns numeric as string in indirection resolution
        assert result == "42"

    # -------------------------------------------------------------------------
    # Triple @@@ and Deep Nesting Tests
    # -------------------------------------------------------------------------

    def test_triple_at_indirection(self, runtime):
        """@@@X resolves three levels of indirection.

        MUMPS: S X="Y" S Y="Z" S Z="W" S W="final" W @@@X  ; writes "final"
        """
        scope = {"X": MArray(), "Y": MArray(), "Z": MArray(), "W": MArray()}
        scope["X"].value = "Y"
        scope["Y"].value = "Z"
        scope["Z"].value = "W"
        scope["W"].value = "final"
        ref = VarRef("@@@X")
        result = _evaluate_subscript(ref, scope, runtime)
        assert result == "final"

    def test_quad_at_indirection(self, runtime):
        """@@@@X resolves four levels of indirection.

        With 4 @ symbols, we need 5 variables in the chain:
        - @A = C (A->"B", B->"C")
        - @@A = D (A->"B", B->"C", C->"D")
        - @@@A = E (A->"B", B->"C", C->"D", D->"E")
        - @@@@A = "final" (A->"B", B->"C", C->"D", D->"E", E->"final")
        """
        scope = {
            "A": MArray(),
            "B": MArray(),
            "C": MArray(),
            "D": MArray(),
            "E": MArray(),
        }
        scope["A"].value = "B"
        scope["B"].value = "C"
        scope["C"].value = "D"
        scope["D"].value = "E"
        scope["E"].value = "final"
        ref = VarRef("@@@@A")
        result = _evaluate_subscript(ref, scope, runtime)
        assert result == "final"

    # -------------------------------------------------------------------------
    # Complex Nested Indirection with Subscripts (II-132.2 Pattern)
    # -------------------------------------------------------------------------

    def test_at_indirection_with_subscript_group(self, runtime):
        """@X@(1) pattern: resolve X then append subscript.

        MUMPS: S X="A" S A(1)=99 W @X@(1)  ; writes 99
        """
        scope = {"X": MArray(), "A": MArray()}
        scope["X"].value = "A"
        scope["A"].set(1, value=99)
        # This is tested via resolve_nested_indirection directly
        result = runtime.resolve_nested_indirection("@X@(1)", scope, return_value=True)
        assert result == "99"

    def test_complex_ii_132_2_pattern_g_chain(self, runtime):
        """Test @G chain where G="@G1", G1="Z", Z="B".

        From II-132.2: @G should follow the @ chain and return "B"
        """
        scope = {"G": MArray(), "G1": MArray(), "Z": MArray()}
        scope["G"].value = "@G1"
        scope["G1"].value = "Z"
        scope["Z"].value = "B"
        ref = VarRef("@G")
        result = _evaluate_subscript(ref, scope, runtime)
        assert result == "B"

    def test_complex_ii_132_2_pattern_h_expression(self, runtime):
        """Test H="@@H1@(@G)@("-")" resolves correctly.

        From II-132.2: The complex nested indirection pattern.
        Setup: G="@G1", G1="Z", Z="B", H1="H(1)", H(1,"B")="I(1)", I(1,"-")="C"
        @H should resolve to "C"
        """
        scope = {
            "G": MArray(),
            "G1": MArray(),
            "Z": MArray(),
            "H": MArray(),
            "H1": MArray(),
            "I": MArray(),
        }
        # From MUMPS:
        # S G="@G1",G1="Z",Z="B",H1="H(1)",H="@@H1@(@G)@("-")",H(1,"B")="I(1)",I(1,"-")="C"
        scope["G"].value = "@G1"
        scope["G1"].value = "Z"
        scope["Z"].value = "B"
        scope["H1"].value = "H(1)"
        scope["H"].value = '@@H1@(@G)@("-")'
        scope["H"].set(1, "B", value="I(1)")
        scope["I"].set(1, "-", value="C")

        ref = VarRef("@H")
        result = _evaluate_subscript(ref, scope, runtime)
        assert result == "C"

    def test_full_ii_132_2_e_expression(self, runtime):
        """Test full E="@A@(@H)" pattern from II-132.2.

        E contains @H which must resolve through the complex chain.
        """
        scope = {
            "G": MArray(),
            "G1": MArray(),
            "Z": MArray(),
            "H": MArray(),
            "H1": MArray(),
            "I": MArray(),
            "A": MArray(),
            "E": MArray(),
            "D": MArray(),
        }
        # Setup from II-132.2
        scope["G"].value = "@G1"
        scope["G1"].value = "Z"
        scope["Z"].value = "B"
        scope["H1"].value = "H(1)"
        scope["H"].value = '@@H1@(@G)@("-")'
        scope["H"].set(1, "B", value="I(1)")
        scope["I"].set(1, "-", value="C")
        scope["A"].value = "D(1,2,3,4,5)"
        scope["E"].value = "@A@(@H)"
        # D(1,2,3,4,5,"C") needs to exist for the final resolution
        scope["D"].set(1, 2, 3, 4, 5, "C", value="result_value")

        # Resolve @E to get the final target name
        resolved = runtime.resolve_nested_indirection("@E", scope, return_value=False)
        assert resolved == 'D(1,2,3,4,5,"C")'

        # Now resolve with return_value=True to get the actual value
        result = runtime.resolve_nested_indirection("@E", scope, return_value=True)
        assert result == "result_value"

    # -------------------------------------------------------------------------
    # Edge Cases and Error Handling
    # -------------------------------------------------------------------------

    def test_at_indirection_empty_value(self, runtime):
        """@X where X is empty string returns empty.

        MUMPS: S X="" W @X  ; writes empty
        """
        scope = {"X": MArray()}
        scope["X"].value = ""
        ref = VarRef("@X")
        result = _evaluate_subscript(ref, scope, runtime)
        assert result == ""

    def test_at_indirection_undefined_source(self, runtime):
        """@X where X is undefined raises IndirectionError."""
        scope = {}  # X not defined
        ref = VarRef("@X")
        with pytest.raises(IndirectionError):
            _evaluate_subscript(ref, scope, runtime)

    def test_at_indirection_with_quoted_string_subscript(self, runtime):
        """@X@("key") pattern with quoted string subscript."""
        scope = {"X": MArray(), "A": MArray()}
        scope["X"].value = "A"
        scope["A"].set("key", value="value_for_key")
        result = runtime.resolve_nested_indirection(
            '@X@("key")', scope, return_value=True
        )
        assert result == "value_for_key"

    def test_fallback_without_runtime_simple_case(self):
        """Test fallback code path when runtime is None (simple indirection)."""
        scope = {"X": MArray(), "A": MArray()}
        scope["X"].value = "A"
        scope["A"].value = "fallback_value"
        ref = VarRef("@X")
        # Call without runtime - uses fallback logic
        result = _evaluate_subscript(ref, scope, runtime=None)
        assert result == "fallback_value"

    def test_fallback_without_runtime_nested(self):
        """Test fallback code path for nested indirection without runtime."""
        scope = {"X": MArray(), "Y": MArray(), "Z": MArray()}
        scope["X"].value = "@Y"
        scope["Y"].value = "Z"
        scope["Z"].value = "nested_value"
        ref = VarRef("@X")
        # Call without runtime - uses fallback logic
        result = _evaluate_subscript(ref, scope, runtime=None)
        assert result == "nested_value"


# =============================================================================
# _evaluate_subscripts with Runtime Tests
# =============================================================================


class TestEvaluateSubscriptsWithRuntime:
    """Tests for _evaluate_subscripts with runtime parameter."""

    @pytest.fixture
    def runtime(self):
        """Create a MUMPSRuntime instance for tests."""
        return MUMPSRuntime()

    def test_evaluate_subscripts_passes_runtime(self, runtime):
        """Ensure runtime is passed through to individual subscript evaluation."""
        scope = {"X": MArray(), "A": MArray()}
        scope["X"].value = "A"
        scope["A"].value = "resolved"

        subs = (1, VarRef("@X"), "key")
        result = _evaluate_subscripts(subs, scope, runtime)
        assert result == (1, "resolved", "key")

    def test_evaluate_subscripts_multiple_indirections(self, runtime):
        """Multiple indirection subscripts all resolve correctly."""
        scope = {
            "X": MArray(),
            "Y": MArray(),
            "A": MArray(),
            "B": MArray(),
        }
        scope["X"].value = "A"
        scope["A"].value = "val_a"
        scope["Y"].value = "B"
        scope["B"].value = "val_b"

        subs = (VarRef("@X"), VarRef("@Y"))
        result = _evaluate_subscripts(subs, scope, runtime)
        assert result == ("val_a", "val_b")

    def test_evaluate_subscripts_complex_indirection(self, runtime):
        """Complex nested indirection in subscript resolves correctly."""
        scope = {
            "X": MArray(),
            "Y": MArray(),
            "Z": MArray(),
        }
        scope["X"].value = "@Y"
        scope["Y"].value = "Z"
        scope["Z"].value = "final"

        subs = (VarRef("@X"),)
        result = _evaluate_subscripts(subs, scope, runtime)
        assert result == ("final",)

    def test_evaluate_subscripts_none_with_runtime(self, runtime):
        """None input returns None even with runtime."""
        assert _evaluate_subscripts(None, {}, runtime) is None

    def test_evaluate_subscripts_empty_with_runtime(self, runtime):
        """Empty tuple returns empty tuple with runtime."""
        assert _evaluate_subscripts((), {}, runtime) == ()


# =============================================================================
# T088: _split_argument_list Tests
# =============================================================================


class TestSplitArgumentList:
    """Tests for _split_argument_list function (T088).

    Feature: 017 T088 - Argument Indirection Command Lists
    Used for KILL @X, NEW @X where X may contain comma-separated
    variable names that include subscripts.
    """

    @pytest.fixture
    def split_arg_list(self):
        """Import the function under test."""

        return _split_argument_list

    def test_simple_single_variable(self, split_arg_list):
        """Single variable returns list with one element."""
        assert split_arg_list("X") == ["X"]
        assert split_arg_list("ABC") == ["ABC"]
        assert split_arg_list("VAR123") == ["VAR123"]

    def test_simple_comma_separated(self, split_arg_list):
        """Simple comma-separated variables split correctly."""
        assert split_arg_list("E,F") == ["E", "F"]
        assert split_arg_list("A,B,C") == ["A", "B", "C"]
        assert split_arg_list("X,Y,Z,W") == ["X", "Y", "Z", "W"]

    def test_subscripted_variable_single(self, split_arg_list):
        """Subscripted variable stays intact."""
        assert split_arg_list("A(1,2)") == ["A(1,2)"]
        assert split_arg_list("ARR(1,2,3)") == ["ARR(1,2,3)"]

    def test_subscripted_with_simple(self, split_arg_list):
        """Subscripted variable combined with simple variable."""
        assert split_arg_list("A(1,2),B") == ["A(1,2)", "B"]
        assert split_arg_list("B,A(1,2)") == ["B", "A(1,2)"]
        assert split_arg_list("A(1,2),B,C") == ["A(1,2)", "B", "C"]

    def test_multiple_subscripted(self, split_arg_list):
        """Multiple subscripted variables."""
        assert split_arg_list("A(1,2),B(3)") == ["A(1,2)", "B(3)"]
        assert split_arg_list("X(1),Y(2,3),Z(4,5,6)") == ["X(1)", "Y(2,3)", "Z(4,5,6)"]

    def test_nested_parentheses(self, split_arg_list):
        """Nested parentheses are handled correctly."""
        # ARR(F(1)) where F(1) is an inner function call representation
        assert split_arg_list("ARR(F(1)),B") == ["ARR(F(1))", "B"]
        assert split_arg_list("A(B(C(1))),D") == ["A(B(C(1)))", "D"]

    def test_quoted_strings_in_subscripts(self, split_arg_list):
        """Quoted strings inside subscripts preserve commas."""
        assert split_arg_list('A("x,y"),B') == ['A("x,y")', "B"]
        assert split_arg_list("A('a,b'),B") == ["A('a,b')", "B"]
        assert split_arg_list('A("x,y","z"),B') == ['A("x,y","z")', "B"]

    def test_empty_string(self, split_arg_list):
        """Empty string returns empty list."""
        assert split_arg_list("") == []

    def test_whitespace_handling(self, split_arg_list):
        """Whitespace around items is trimmed."""
        assert split_arg_list("A , B") == ["A", "B"]
        assert split_arg_list("  X  ,  Y  ") == ["X", "Y"]
        assert split_arg_list("A(1, 2) , B") == ["A(1, 2)", "B"]

    def test_global_variables(self, split_arg_list):
        """Global variables (with ^) are handled."""
        assert split_arg_list("^GLO,^VAR") == ["^GLO", "^VAR"]
        assert split_arg_list("^G(1,2),A") == ["^G(1,2)", "A"]

    def test_mixed_globals_and_locals(self, split_arg_list):
        """Mix of global and local variables."""
        assert split_arg_list("A,^B,C(1),^D(2,3)") == ["A", "^B", "C(1)", "^D(2,3)"]

    def test_runtime_method_access(self):
        """_split_argument_list is accessible via MUMPSRuntime."""
        runtime = MUMPSRuntime()
        result = runtime._split_argument_list("A,B(1,2),C")
        assert result == ["A", "B(1,2)", "C"]
