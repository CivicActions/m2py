"""Tests for indirection resolution methods (Spec 017).

Tests the new runtime methods for resolving name indirection:
- resolve_indirection_name: Multi-level indirection for FOR loops
- resolve_for_indirection: FOR loop indirection with nested resolution
- resolve_nested_indirection: Recursive indirection resolution
- get_indirection_source: Extended to handle subscripted names

Reference: MUMPS allows complex indirection chains like @A where A="@B",
B="@$E(""XYZ"",2)" which resolves to "Y".
"""

import pytest
from m2py.runtime import MArray, MUMPSRuntime, IndirectionError


# =============================================================================
# MUMPSRuntime.resolve_indirection_name Tests
# =============================================================================


class TestResolveIndirectionName:
    """Tests for resolve_indirection_name method.

    This method returns the final variable NAME (not value) after
    resolving multiple levels of indirection.
    """

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_single_level_simple(self, rt):
        """Single level @A where A="B" returns "B"."""
        scope = {"A": MArray()}
        scope["A"].value = "B"
        result = rt.resolve_indirection_name("A", 1, scope)
        assert result == "B"

    def test_double_level(self, rt):
        """Double level @@A where A="X", X="Y" returns "Y"."""
        scope = {"A": MArray(), "X": MArray()}
        scope["A"].value = "X"
        scope["X"].value = "Y"
        result = rt.resolve_indirection_name("A", 2, scope)
        assert result == "Y"

    def test_triple_level(self, rt):
        """Triple level @@@A where A="X", X="Y", Y="Z" returns "Z"."""
        scope = {"A": MArray(), "X": MArray(), "Y": MArray()}
        scope["A"].value = "X"
        scope["X"].value = "Y"
        scope["Y"].value = "Z"
        result = rt.resolve_indirection_name("A", 3, scope)
        assert result == "Z"

    def test_undefined_source_raises(self, rt):
        """Undefined source variable raises IndirectionError."""
        scope = {}
        with pytest.raises(IndirectionError) as exc_info:
            rt.resolve_indirection_name("UNDEF", 1, scope)
        assert "Undefined local variable" in str(exc_info.value)

    def test_empty_value_raises(self, rt):
        """Empty value at any level raises IndirectionError."""
        scope = {"A": MArray()}
        scope["A"].value = ""
        with pytest.raises(IndirectionError) as exc_info:
            rt.resolve_indirection_name("A", 1, scope)
        assert "empty variable name" in str(exc_info.value)

    def test_intermediate_undefined_raises(self, rt):
        """Undefined intermediate variable raises error."""
        scope = {"A": MArray()}
        scope["A"].value = "NONEXISTENT"
        with pytest.raises(IndirectionError):
            rt.resolve_indirection_name("A", 2, scope)

    def test_level_zero_returns_varname(self, rt):
        """Zero levels returns the original varname."""
        scope = {"A": MArray()}
        scope["A"].value = "X"
        # levels=0 should just return the input name without resolution
        result = rt.resolve_indirection_name("A", 0, scope)
        assert result == "A"


# =============================================================================
# MUMPSRuntime.resolve_for_indirection Tests
# =============================================================================


class TestResolveForIndirection:
    """Tests for resolve_for_indirection method.

    This method handles FOR loop indirection including nested @ in values.
    """

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_simple_resolution(self, rt):
        """Simple case: A="B" resolves to "B"."""
        scope = {"A": MArray()}
        scope["A"].value = "B"
        result = rt.resolve_for_indirection("A", scope)
        assert result == "B"

    def test_undefined_raises(self, rt):
        """Undefined source raises IndirectionError."""
        with pytest.raises(IndirectionError):
            rt.resolve_for_indirection("UNDEF", {})

    def test_value_with_leading_at_resolved(self, rt):
        """Value starting with @ triggers nested resolution."""
        scope = {"A": MArray(), "B": MArray()}
        scope["A"].value = "@B"
        scope["B"].value = "C"
        result = rt.resolve_for_indirection("A", scope)
        assert result == "C"


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
        scope = {"A": MArray(), "I": MArray()}
        scope["A"][1].value = "RESULT"
        scope["I"].value = 1
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
# MUMPSRuntime.get_indirection_source Extended Tests
# =============================================================================


class TestGetIndirectionSourceExtended:
    """Extended tests for get_indirection_source with subscripted names."""

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_simple_variable(self, rt):
        """Simple variable returns its value."""
        scope = {"X": MArray()}
        scope["X"].value = "VALUE"
        result = rt.get_indirection_source("X", scope)
        assert result == "VALUE"

    def test_subscripted_variable(self, rt):
        """Subscripted variable like X(1) returns value."""
        scope = {"X": MArray()}
        scope["X"][1].value = "SUB_VALUE"
        result = rt.get_indirection_source("X(1)", scope)
        assert result == "SUB_VALUE"

    def test_deep_subscript(self, rt):
        """Deep subscript like X(1,2,3) returns value."""
        scope = {"X": MArray()}
        scope["X"][1, 2, 3].value = "DEEP"
        result = rt.get_indirection_source("X(1,2,3)", scope)
        assert result == "DEEP"

    def test_undefined_simple_raises(self, rt):
        """Undefined simple variable raises IndirectionError."""
        with pytest.raises(IndirectionError) as exc_info:
            rt.get_indirection_source("UNDEF", {})
        assert "Undefined local variable" in str(exc_info.value)

    def test_undefined_subscript_raises(self, rt):
        """Undefined subscript raises IndirectionError."""
        scope = {"X": MArray()}
        scope["X"][1].value = "exists"
        # X(2) doesn't exist
        with pytest.raises(IndirectionError) as exc_info:
            rt.get_indirection_source("X(2)", scope)
        assert "Undefined local variable" in str(exc_info.value)

    def test_marray_value_converted_to_string(self, rt):
        """MArray value is converted to string."""
        scope = {"X": MArray()}
        scope["X"].value = 42  # numeric
        result = rt.get_indirection_source("X", scope)
        assert result == "42"
        assert isinstance(result, str)


# =============================================================================
# Integration: Complex Indirection Chains
# =============================================================================


class TestComplexIndirectionChains:
    """Integration tests for complex indirection scenarios."""

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_for_loop_indirect_to_subscripted(self, rt):
        """F @A where A="B(1)" - indirect to subscripted var name."""
        scope = {"A": MArray(), "B": MArray()}
        scope["A"].value = "B"
        scope["B"][1].value = 0
        # resolve_indirection_name gets the NAME, not value
        result = rt.resolve_indirection_name("A", 1, scope)
        assert result == "B"

    def test_mixed_global_local(self, rt):
        """Indirection mixing global and local variables."""
        scope = {"L": MArray()}
        rt.globals.set("G", (), "^RESULT")
        scope["L"].value = "^G"
        # Resolve L → "^G"
        name = rt.resolve_indirection_name("L", 1, scope)
        assert name == "^G"
        # Now get the global's value
        value = rt.get_var(name, scope)
        assert value == "^RESULT"

    def test_numeric_subscript_in_chain(self, rt):
        """Subscripts with numeric values in chain."""
        scope = {"A": MArray(), "I": MArray()}
        scope["A"][1, 2].value = "FINAL"
        scope["I"].value = "A(1,2)"
        result = rt.resolve_indirection_name("I", 1, scope)
        assert result == "A(1,2)"
