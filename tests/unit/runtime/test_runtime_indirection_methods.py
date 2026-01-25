"""Tests for MUMPSRuntime indirection methods (Spec 017 Phase 6).

Tests the runtime methods for indirection support:
1. get_data() - $DATA with indirected variable names
2. kill_var() - KILL with indirected variable names

Reference: MUMPS 1995 ANSI Standard
"""

import pytest
from m2py.runtime import MArray, MUMPSRuntime, IndirectionError


# =============================================================================
# MUMPSRuntime.get_data() Tests
# =============================================================================


class TestRuntimeGetData:
    """Tests for MUMPSRuntime.get_data() method.

    get_data() implements $DATA for indirected variables, parsing the
    variable name string to determine if it's local or global.
    """

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_get_data_undefined_local(self, rt):
        """get_data returns 0 for undefined local variable."""
        scope = {}
        assert rt.get_data("X", scope) == 0

    def test_get_data_defined_local_value_only(self, rt):
        """get_data returns 1 for defined local with value, no descendants."""
        scope = {"X": MArray()}
        scope["X"].value = "test"
        assert rt.get_data("X", scope) == 1

    def test_get_data_defined_local_with_descendants(self, rt):
        """get_data returns 11 for defined local with value and descendants."""
        scope = {"X": MArray()}
        scope["X"].value = "test"
        scope["X"][1].value = "child"
        assert rt.get_data("X", scope) == 11

    def test_get_data_local_descendants_only(self, rt):
        """get_data returns 10 for local with descendants but no value."""
        scope = {"X": MArray()}
        scope["X"][1].value = "child"
        assert rt.get_data("X", scope) == 10

    def test_get_data_subscripted_local(self, rt):
        """get_data with subscripted local variable name."""
        scope = {"ARR": MArray()}
        scope["ARR"][1, 2].value = "test"
        assert rt.get_data("ARR(1,2)", scope) == 1

    def test_get_data_subscripted_local_undefined(self, rt):
        """get_data returns 0 for undefined subscript."""
        scope = {"ARR": MArray()}
        scope["ARR"][1].value = "test"
        assert rt.get_data("ARR(2)", scope) == 0

    def test_get_data_global_undefined(self, rt):
        """get_data returns 0 for undefined global."""
        scope = {}
        assert rt.get_data("^G", scope) == 0

    def test_get_data_global_defined(self, rt):
        """get_data returns 1 for defined global."""
        scope = {}
        rt.globals.set("G", (), "test")
        assert rt.get_data("^G", scope) == 1

    def test_get_data_global_subscripted(self, rt):
        """get_data with subscripted global variable name."""
        scope = {}
        rt.globals.set("G", ("1", "2"), "test")
        assert rt.get_data("^G(1,2)", scope) == 1

    def test_get_data_empty_name(self, rt):
        """get_data returns 0 for empty name."""
        scope = {}
        assert rt.get_data("", scope) == 0

    # -------------------------------------------------------------------------
    # V1IDNM3 Edge Cases: Nested indirection, naked refs, subscript evaluation
    # -------------------------------------------------------------------------

    def test_get_data_nested_indirection(self, rt):
        """get_data resolves nested indirection (@name) before checking $DATA.

        When name starts with @, resolve_nested_indirection is called first
        to resolve the actual variable name.
        """
        scope = {"X": MArray(), "REF": MArray()}
        scope["X"][1].value = "test"
        scope["REF"].value = "X(1)"  # @REF resolves to "X(1)"
        # @REF should resolve to X(1) which has value
        assert rt.get_data("@REF", scope) == 1

    def test_get_data_nested_indirection_undefined_target(self, rt):
        """get_data with nested indirection to undefined variable returns 0."""
        scope = {"REF": MArray()}
        scope["REF"].value = "NOTHERE"  # Points to undefined var
        assert rt.get_data("@REF", scope) == 0

    def test_get_data_nested_indirection_empty_resolution(self, rt):
        """get_data returns 0 when nested indirection resolves to empty."""
        scope = {"REF": MArray()}
        scope["REF"].value = ""  # Empty target
        assert rt.get_data("@REF", scope) == 0

    def test_get_data_naked_global_reference(self, rt):
        """get_data handles naked global references ^(subs).

        When the global name is just "^", resolve_naked() is called to get
        the actual global name from the naked indicator.
        """
        scope = {}
        # First access ^G to set the naked indicator
        rt.globals.set("G", ("1",), "value")
        rt.get_var("^G(1)", scope)  # Sets naked indicator to G
        # Now ^(2) should check $D(^G(2))
        rt.globals.set("G", ("2",), "another")
        assert rt.get_data("^(2)", scope) == 1

    def test_get_data_naked_global_undefined(self, rt):
        """get_data with naked reference to undefined subscript returns 0."""
        scope = {}
        rt.globals.set("G", ("1",), "value")
        rt.get_var("^G(1)", scope)  # Sets naked indicator to G
        # ^(2) doesn't exist
        assert rt.get_data("^(2)", scope) == 0

    def test_get_data_subscript_evaluation_with_varref(self, rt):
        """get_data evaluates VarRef subscripts to their actual values.

        When subscripts contain variable references like A(I) where I is a
        variable, _evaluate_subscripts resolves them to actual values.
        """

        scope = {"ARR": MArray(), "I": MArray()}
        scope["ARR"][5].value = "found"
        scope["I"].value = 5
        # This simulates get_data("ARR(I)") where I is resolved via VarRef
        # In actual code, the parser creates VarRef objects for variable subscripts
        # Here we test that string subscript "5" works correctly
        assert rt.get_data("ARR(5)", scope) == 1


# =============================================================================
# MUMPSRuntime.kill_var() Tests
# =============================================================================


class TestRuntimeKillVar:
    """Tests for MUMPSRuntime.kill_var() method.

    kill_var() implements KILL with indirection, parsing the variable
    name string to determine if it's local or global.
    """

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_kill_var_local_entire(self, rt):
        """kill_var removes entire local variable."""
        scope = {"X": MArray()}
        scope["X"].value = "test"
        rt.kill_var("X", scope)
        assert "X" not in scope

    def test_kill_var_local_subscripted(self, rt):
        """kill_var at subscript removes that subscript only."""
        scope = {"ARR": MArray()}
        scope["ARR"][1].value = "one"
        scope["ARR"][2].value = "two"
        rt.kill_var("ARR(1)", scope)
        # ARR still exists, but ARR(1) should be undefined
        assert "ARR" in scope
        assert scope["ARR"].get(1) == ""  # Killed
        assert scope["ARR"].get(2) == "two"  # Untouched

    def test_kill_var_local_deep_subscript(self, rt):
        """kill_var with deep subscript."""
        scope = {"ARR": MArray()}
        scope["ARR"][1, 2, 3].value = "deep"
        scope["ARR"][1, 2].value = "shallow"
        rt.kill_var("ARR(1,2,3)", scope)
        assert scope["ARR"].get(1, 2, 3) == ""  # Killed
        assert scope["ARR"].get(1, 2) == "shallow"  # Untouched

    def test_kill_var_local_nonexistent(self, rt):
        """kill_var on nonexistent variable is a no-op."""
        scope = {}
        # Should not raise an error
        rt.kill_var("X", scope)
        assert "X" not in scope

    def test_kill_var_global_entire(self, rt):
        """kill_var removes entire global variable."""
        scope = {}
        rt.globals.set("G", (), "test")
        rt.kill_var("^G", scope)
        # After kill, get returns None (or empty string depending on storage)
        result = rt.globals.get("G", ())
        assert result in (None, "")

    def test_kill_var_global_subscripted(self, rt):
        """kill_var at global subscript removes that subscript only."""
        scope = {}
        rt.globals.set("G", ("1",), "one")
        rt.globals.set("G", ("2",), "two")
        rt.kill_var("^G(1)", scope)
        # After kill, get returns None (or empty string depending on storage)
        result = rt.globals.get("G", ("1",))
        assert result in (None, "")  # Killed
        assert rt.globals.get("G", ("2",)) == "two"  # Untouched

    def test_kill_var_empty_name_raises(self, rt):
        """kill_var raises IndirectionError for empty name."""
        scope = {}
        with pytest.raises(IndirectionError):
            rt.kill_var("", scope)

    def test_kill_var_invalid_name_raises(self, rt):
        """kill_var raises IndirectionError for invalid variable name."""
        scope = {}
        with pytest.raises(IndirectionError):
            rt.kill_var("123BAD", scope)


# =============================================================================
# MUMPSRuntime._test attribute Tests
# =============================================================================


class TestRuntimeTestAttribute:
    """Tests for MUMPSRuntime._test attribute initialization.

    Bug fix: _test attribute must be initialized for XECUTE to sync
    $TEST value properly.
    """

    def test_test_attribute_exists(self):
        """MUMPSRuntime has _test attribute initialized."""
        rt = MUMPSRuntime()
        assert hasattr(rt, "_test")

    def test_test_attribute_initial_value(self):
        """MUMPSRuntime._test is False initially."""
        rt = MUMPSRuntime()
        assert rt._test is False

    def test_test_attribute_can_be_set(self):
        """MUMPSRuntime._test can be modified."""
        rt = MUMPSRuntime()
        rt._test = True
        assert rt._test is True


# =============================================================================
# MUMPSRuntime.append_subscripts() Tests
# =============================================================================


class TestRuntimeAppendSubscripts:
    """Tests for MUMPSRuntime.append_subscripts() method.

    Spec 017 Phase 6: append_subscripts properly merges subscripts for
    name indirection like @A@(1,2) where A="B(3,4)" → "B(3,4,1,2)".
    """

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_no_existing_subscripts(self, rt):
        """Base name without subscripts gets new subscripts added."""
        result = rt.append_subscripts("X", 1, 2)
        assert result == "X(1,2)"

    def test_single_new_subscript(self, rt):
        """Single subscript added to base name."""
        result = rt.append_subscripts("B", 1)
        assert result == "B(1)"

    def test_merge_with_existing_subscripts(self, rt):
        """New subscripts merged with existing subscripts."""
        result = rt.append_subscripts("ARR(1)", 2, 3)
        assert result == "ARR(1,2,3)"

    def test_deeply_nested_subscripts(self, rt):
        """Deep nesting: B(1,2,3) + (4,5) → B(1,2,3,4,5)."""
        result = rt.append_subscripts("B(1,2,3)", 4, 5)
        assert result == "B(1,2,3,4,5)"

    def test_string_subscripts_quoted(self, rt):
        """String subscripts are properly quoted."""
        result = rt.append_subscripts("ARR", "key")
        assert result == 'ARR("key")'

    def test_mixed_numeric_and_string_subscripts(self, rt):
        """Mixed numeric and string subscripts handled correctly."""
        result = rt.append_subscripts("ARR(1)", "two", 3)
        assert result == 'ARR(1,"two",3)'

    def test_string_with_quotes_escaped(self, rt):
        """Strings containing quotes are properly escaped."""
        result = rt.append_subscripts("ARR", 'say "hello"')
        assert result == 'ARR("say ""hello""")'

    def test_empty_additional_subscripts_returns_base(self, rt):
        """No additional subscripts returns base name unchanged."""
        result = rt.append_subscripts("ARR(1,2)")
        assert result == "ARR(1,2)"

    def test_global_variable_base(self, rt):
        """Global variable base name handled correctly."""
        result = rt.append_subscripts("^GLO(1)", 2, 3)
        assert result == "^GLO(1,2,3)"

    def test_global_no_existing_subscripts(self, rt):
        """Global without subscripts gets new subscripts."""
        result = rt.append_subscripts("^GLO", 1, 2)
        assert result == "^GLO(1,2)"

    def test_existing_string_subscript_preserved(self, rt):
        """Existing string subscripts in base are preserved."""
        # Base has a string subscript
        result = rt.append_subscripts('ARR("a")', "b")
        assert result == 'ARR("a","b")'

    def test_empty_string_subscript(self, rt):
        """Empty string as subscript is valid."""
        result = rt.append_subscripts("ARR", "")
        assert result == 'ARR("")'

    def test_numeric_string_subscript(self, rt):
        """Numeric looking string remains quoted as string."""
        result = rt.append_subscripts("ARR(1)", "2")
        assert result == 'ARR(1,"2")'

    def test_zero_subscript(self, rt):
        """Zero as subscript works correctly."""
        result = rt.append_subscripts("ARR", 0)
        assert result == "ARR(0)"

    def test_negative_subscript(self, rt):
        """Negative number as subscript."""
        result = rt.append_subscripts("ARR", -1)
        assert result == "ARR(-1)"


# =============================================================================
# MUMPSRuntime.merge_var() Tests (Phase 13)
# =============================================================================


class TestRuntimeMergeVar:
    """Tests for MUMPSRuntime.merge_var() method.

    Spec 017 Phase 13: merge_var() implements MERGE with indirection
    destination, merging a source MArray tree into a variable by name.
    """

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_merge_var_to_local_simple(self, rt):
        """merge_var copies source tree to local variable."""
        scope = {}
        src = MArray()
        src[1].value = "one"
        src[2].value = "two"
        rt.merge_var("B", src, scope)
        assert "B" in scope
        assert scope["B"].get(1) == "one"
        assert scope["B"].get(2) == "two"

    def test_merge_var_to_local_subscripted(self, rt):
        """merge_var with subscripted destination name."""
        scope = {"B": MArray()}
        src = MArray()
        src[1].value = "one"
        src[2].value = "two"
        rt.merge_var("B(3)", src, scope)
        assert scope["B"].get(3, 1) == "one"
        assert scope["B"].get(3, 2) == "two"

    def test_merge_var_to_local_preserves_existing(self, rt):
        """merge_var preserves existing nodes in destination."""
        scope = {"B": MArray()}
        scope["B"][5].value = "old"
        src = MArray()
        src[1].value = "new"
        rt.merge_var("B", src, scope)
        assert scope["B"].get(1) == "new"  # Merged
        assert scope["B"].get(5) == "old"  # Preserved

    def test_merge_var_to_global_simple(self, rt):
        """merge_var copies source tree to global variable."""
        scope = {}
        src = MArray()
        src[1].value = "one"
        src[2].value = "two"
        rt.merge_var("^G", src, scope)
        assert rt.globals.get("G", ("1",)) == "one"
        assert rt.globals.get("G", ("2",)) == "two"

    def test_merge_var_to_global_subscripted(self, rt):
        """merge_var with subscripted global destination."""
        scope = {}
        src = MArray()
        src[1].value = "one"
        rt.merge_var("^G(3)", src, scope)
        assert rt.globals.get("G", ("3", "1")) == "one"

    def test_merge_var_merges_root_value(self, rt):
        """merge_var copies source root value if present."""
        scope = {}
        src = MArray()
        src.value = "root"
        src[1].value = "child"
        rt.merge_var("B", src, scope)
        assert scope["B"].value == "root"
        assert scope["B"].get(1) == "child"

    def test_merge_var_none_source_is_noop(self, rt):
        """merge_var with None source does nothing."""
        scope = {}
        rt.merge_var("B", None, scope)
        assert "B" not in scope

    def test_merge_var_empty_name_raises(self, rt):
        """merge_var raises IndirectionError for empty name."""
        scope = {}
        src = MArray()
        with pytest.raises(IndirectionError):
            rt.merge_var("", src, scope)

    def test_merge_var_invalid_name_raises(self, rt):
        """merge_var raises IndirectionError for invalid variable name."""
        scope = {}
        src = MArray()
        with pytest.raises(IndirectionError):
            rt.merge_var("123BAD", src, scope)

    def test_merge_var_creates_destination_if_missing(self, rt):
        """merge_var creates destination variable if it doesn't exist."""
        scope = {}
        src = MArray()
        src[1].value = "one"
        rt.merge_var("NEWVAR", src, scope)
        assert "NEWVAR" in scope
        assert scope["NEWVAR"].get(1) == "one"

    def test_merge_var_deep_subscripts(self, rt):
        """merge_var with deeply nested subscripted destination."""
        scope = {"ARR": MArray()}
        src = MArray()
        src[1].value = "deep"
        rt.merge_var("ARR(1,2,3)", src, scope)
        assert scope["ARR"].get(1, 2, 3, 1) == "deep"


# =============================================================================
# MUMPSRuntime.get_tree_var() Tests (Phase 13)
# =============================================================================


class TestRuntimeGetTreeVar:
    """Tests for MUMPSRuntime.get_tree_var() method.

    Spec 017 Phase 13: get_tree_var() implements MERGE with indirection
    source, returning an MArray tree for a variable by name.
    """

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_get_tree_var_local_simple(self, rt):
        """get_tree_var returns local variable tree."""
        scope = {"A": MArray()}
        scope["A"][1].value = "one"
        scope["A"][2].value = "two"
        result = rt.get_tree_var("A", scope)
        assert result is not None
        assert result.get(1) == "one"
        assert result.get(2) == "two"

    def test_get_tree_var_local_subscripted(self, rt):
        """get_tree_var with subscripted name returns subtree."""
        scope = {"A": MArray()}
        scope["A"][1, 1].value = "deep1"
        scope["A"][1, 2].value = "deep2"
        result = rt.get_tree_var("A(1)", scope)
        assert result is not None
        assert result.get(1) == "deep1"
        assert result.get(2) == "deep2"

    def test_get_tree_var_global_simple(self, rt):
        """get_tree_var returns global variable tree."""
        scope = {}
        rt.globals.set("G", ("1",), "one")
        rt.globals.set("G", ("2",), "two")
        result = rt.get_tree_var("^G", scope)
        assert result is not None
        # Global trees are MArray copies
        assert result.get(1) == "one" or result.get("1") == "one"

    def test_get_tree_var_global_subscripted(self, rt):
        """get_tree_var with subscripted global returns subtree."""
        scope = {}
        rt.globals.set("G", ("1", "1"), "deep1")
        rt.globals.set("G", ("1", "2"), "deep2")
        result = rt.get_tree_var("^G(1)", scope)
        assert result is not None

    def test_get_tree_var_undefined_local_returns_none(self, rt):
        """get_tree_var returns None for undefined local."""
        scope = {}
        result = rt.get_tree_var("NOTHERE", scope)
        assert result is None

    def test_get_tree_var_undefined_global_returns_none(self, rt):
        """get_tree_var returns None for undefined global."""
        scope = {}
        result = rt.get_tree_var("^NOTHERE", scope)
        assert result is None

    def test_get_tree_var_empty_name_raises(self, rt):
        """get_tree_var raises IndirectionError for empty name."""
        scope = {}
        with pytest.raises(IndirectionError):
            rt.get_tree_var("", scope)

    def test_get_tree_var_invalid_name_raises(self, rt):
        """get_tree_var raises IndirectionError for invalid name."""
        scope = {}
        with pytest.raises(IndirectionError):
            rt.get_tree_var("123BAD", scope)

    def test_get_tree_var_includes_root_value(self, rt):
        """get_tree_var returns tree including root value."""
        scope = {"A": MArray()}
        scope["A"].value = "root"
        scope["A"][1].value = "child"
        result = rt.get_tree_var("A", scope)
        assert result is not None
        assert result.value == "root"
        assert result.get(1) == "child"

    def test_get_tree_var_non_array_returns_none(self, rt):
        """get_tree_var returns None if variable is not an MArray."""
        # This shouldn't normally happen, but test defensive behavior
        scope = {"X": "just a string"}
        result = rt.get_tree_var("X", scope)
        assert result is None
