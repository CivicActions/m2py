"""Tests for VarRef class and subscript evaluation functions.

Tests the new VarRef wrapper class and _evaluate_subscript(s) functions
that enable runtime variable reference resolution in subscripts.

Reference: MUMPS allows variable references in subscripts like @A(I)
where I is a variable that needs to be looked up at runtime.
"""

import pytest
from m2py.runtime import MArray
from m2py.runtime import (
    VarRef,
    _evaluate_subscript,
    _evaluate_subscripts,
    _convert_subscript,
    _parse_subscripted_name,
    IndirectionError,
)


# =============================================================================
# VarRef Class Tests
# =============================================================================


class TestVarRef:
    """Tests for the VarRef wrapper class."""

    def test_varref_creation(self):
        """VarRef stores variable name."""
        ref = VarRef("X")
        assert ref.name == "X"

    def test_varref_repr(self):
        """VarRef has readable repr."""
        ref = VarRef("MYVAR")
        assert repr(ref) == "VarRef('MYVAR')"

    def test_varref_different_names(self):
        """VarRef preserves different variable names."""
        ref1 = VarRef("A")
        ref2 = VarRef("B")
        assert ref1.name == "A"
        assert ref2.name == "B"

    def test_varref_empty_name(self):
        """VarRef accepts empty name (edge case)."""
        ref = VarRef("")
        assert ref.name == ""


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
