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
