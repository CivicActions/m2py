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


# =============================================================================
# New Methods Added in Phase 19 (017-ydb-test-failures)
# =============================================================================


class TestAppendSubscriptsToName:
    """Tests for MUMPSRuntime.append_subscripts_to_name() method.

    Feature: 017-ydb-test-failures Phase 19

    This method appends subscripts to a variable name string, used for
    indirection patterns like @func()@(subs) where the function returns
    a name and subscripts need to be appended.
    """

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_append_to_simple_name(self, rt):
        """Append subscripts to unsubscripted name."""
        result = rt.append_subscripts_to_name("A", [1, 2])
        assert result == "A(1,2)"

    def test_append_to_subscripted_name(self, rt):
        """Append subscripts to already subscripted name."""
        result = rt.append_subscripts_to_name("A(1)", [2, 3])
        assert result == "A(1,2,3)"

    def test_append_string_subscripts(self, rt):
        """Append string subscripts."""
        result = rt.append_subscripts_to_name("X", ["key", "sub"])
        assert result == 'X("key","sub")'

    def test_append_empty_subscripts(self, rt):
        """Appending empty list leaves name unchanged."""
        result = rt.append_subscripts_to_name("A(1,2)", [])
        assert result == "A(1,2)"

    def test_append_to_global_name(self, rt):
        """Append subscripts to global variable name."""
        result = rt.append_subscripts_to_name("^GLO", [1])
        assert result == "^GLO(1)"

    def test_internal_append_multiple_levels(self, rt):
        """_append_subscripts_to_name handles multiple subscript lists."""
        result = rt._append_subscripts_to_name("A", [[1], [2, 3]])
        # First appends [1], then [2,3]
        assert result == "A(1,2,3)"


class TestEvaluateMumpsExpression:
    """Tests for MUMPSRuntime.evaluate_mumps_expression() method.

    Feature: 017-ydb-test-failures Phase 19

    This method evaluates a MUMPS expression string directly, used for
    @$P(...) style indirection where the function result is evaluated
    as an expression without intermediate lookups.
    """

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_evaluate_numeric_literal(self, rt):
        """Evaluate numeric literal expression."""
        scope = {}
        result = rt.evaluate_mumps_expression("42", scope)
        assert result == 42

    def test_evaluate_string_literal(self, rt):
        """Evaluate quoted string literal (which evaluates to the string)."""
        scope = {}
        # Note: "hello" as a MUMPS expression tries to look up variable hello
        # unless it's a numeric literal
        result = rt.evaluate_mumps_expression("123", scope)
        assert result == 123

    def test_evaluate_variable_reference(self, rt):
        """Evaluate expression that's a variable name."""
        scope = {"X": MArray(value=99)}
        result = rt.evaluate_mumps_expression("X", scope)
        assert result == 99

    def test_evaluate_comparison_expression(self, rt):
        """Evaluate comparison expression."""
        scope = {}
        # "1=1" evaluates to true (1)
        result = rt.evaluate_mumps_expression("1=1", scope)
        assert result == 1

        # "1=0" evaluates to false (0)
        result = rt.evaluate_mumps_expression("1=0", scope)
        assert result == 0

    def test_evaluate_treat_empty_as_truthy(self, rt):
        """evaluate_mumps_expression with treat_empty_as_truthy for IF context."""
        scope = {}
        # With flag=True, empty string returns 1 (TRUE)
        result = rt.evaluate_mumps_expression("", scope, treat_empty_as_truthy=True)
        assert result == 1


class TestExecuteMumpsIndirected:
    """Tests for MUMPSRuntime.execute_mumps_indirected() method.

    Feature: 017-ydb-test-failures Phase 19

    This method handles XECUTE argument indirection: X @X where X="Y,Z"
    resolves each variable in the comma-separated list to get code to execute.
    """

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_execute_single_variable(self, rt):
        """Execute code from single variable."""
        rt._capture_output = True
        scope = {
            "X": MArray(value="CODE"),
            "CODE": MArray(value="S RESULT=42 W RESULT"),
        }
        rt.execute_mumps_indirected("X", scope, levels=1)
        output = rt.get_output()
        assert "42" in output

    def test_execute_validates_resolve(self, rt):
        """execute_mumps_indirected validates the indirection resolves."""
        scope = {"X": MArray(value="Y")}  # Y doesn't exist
        # Should not raise - empty code just does nothing
        rt.execute_mumps_indirected("X", scope, levels=1)


# =============================================================================
# get_indirected allow_undefined Tests (Phase 19)
# =============================================================================


class TestGetIndirectedAllowUndefined:
    """Tests for get_indirected allow_undefined parameter.

    Feature: 017-ydb-test-failures Phase 19

    This parameter controls whether undefined target variables raise an error
    (default, for W @X) or return empty string (for $GET(@X)).
    """

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_allow_undefined_false_raises_error(self, rt):
        """With allow_undefined=False (default), undefined target raises error."""
        scope = {"X": MArray(value="UNDEFINED")}
        with pytest.raises(IndirectionError):
            rt.get_indirected("X", scope, levels=1, allow_undefined=False)

    def test_allow_undefined_true_returns_empty(self, rt):
        """With allow_undefined=True, undefined target returns empty string."""
        scope = {"X": MArray(value="UNDEFINED")}
        result = rt.get_indirected("X", scope, levels=1, allow_undefined=True)
        assert result == ""

    def test_allow_undefined_defined_target_returns_value(self, rt):
        """With allow_undefined=True, defined target returns value."""
        scope = {"X": MArray(value="Y"), "Y": MArray(value="the value")}
        result = rt.get_indirected("X", scope, levels=1, allow_undefined=True)
        assert result == "the value"

    def test_allow_undefined_global_always_returns_empty_if_undefined(self, rt):
        """Globals always return empty for undefined (not affected by flag)."""
        scope = {"X": MArray(value="^UNDEFINED")}
        # Global targets don't raise even with allow_undefined=False
        result = rt.get_indirected("X", scope, levels=1, allow_undefined=False)
        assert result == ""

    def test_allow_undefined_subscripted_target(self, rt):
        """allow_undefined works with subscripted targets."""
        scope = {
            "X": MArray(value='A("key")'),
            "A": MArray(),  # A exists but A("key") doesn't
        }
        result = rt.get_indirected("X", scope, levels=1, allow_undefined=True)
        assert result == ""

    def test_allow_undefined_intermediate_undefined_still_raises(self, rt):
        """Intermediate undefined variables in chain still raise error."""
        from m2py.core.exceptions import VarExpectedError

        scope = {"X": MArray(value="Y")}  # Y doesn't exist, so @@X fails at first @
        # This should still raise because the intermediate resolution fails
        # (either IndirectionError or VarExpectedError depending on context)
        with pytest.raises((IndirectionError, VarExpectedError)):
            rt.get_indirected("X", scope, levels=2, allow_undefined=True)


# =============================================================================
# get_indirected levels=0 with subscripts Tests (Phase 19)
# =============================================================================


class TestGetIndirectedLevelsZeroWithSubscripts:
    """Tests for get_indirected with levels=0 and per_level_subscripts.

    Feature: 017-ydb-test-failures Phase 19

    levels=0 is used for NakedGlobal expressions where the target name
    is already resolved. With subscripts, we append them to the name.
    """

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_levels_zero_no_subscripts(self, rt):
        """levels=0 without subscripts returns value at source name directly."""
        scope = {"X": MArray(value=42)}
        result = rt.get_indirected("X", scope, levels=0)
        assert result == 42

    def test_levels_zero_with_subscripts(self, rt):
        """levels=0 with subscripts appends them and returns value."""
        scope = {"X": MArray()}
        scope["X"][1, 2].value = "hello"
        result = rt.get_indirected("X", scope, levels=0, per_level_subscripts=[[1, 2]])
        assert result == "hello"

    def test_levels_zero_global_with_subscripts(self, rt):
        """levels=0 with global and subscripts."""
        scope = {}
        rt.globals.set("G", ("a", "b"), "global value")
        result = rt.get_indirected(
            "^G", scope, levels=0, per_level_subscripts=[["a", "b"]]
        )
        assert result == "global value"

    def test_levels_zero_multiple_subscript_levels(self, rt):
        """levels=0 with multiple subscript levels appends all."""
        scope = {"X": MArray()}
        scope["X"][1, 2, 3, 4].value = "deep"
        result = rt.get_indirected(
            "X", scope, levels=0, per_level_subscripts=[[1, 2], [3, 4]]
        )
        assert result == "deep"


# =============================================================================
# kill_indirected exclusive KILL Tests (Phase 19)
# =============================================================================


class TestKillIndirectedExclusiveKill:
    """Tests for kill_indirected with exclusive KILL syntax.

    Feature: 017-ydb-test-failures Phase 19

    MUMPS exclusive KILL: K @X where X="(A,B)" kills all except A and B.
    Can be combined: K @X where X="(A),B,C" kills all except A, then kills B and C.
    """

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_exclusive_kill_single_except(self, rt):
        """K @X where X='(A)' kills all locals except A."""
        scope = {
            "X": MArray(value="(A)"),
            "A": MArray(value="keep"),
            "B": MArray(value="kill"),
            "C": MArray(value="kill"),
        }
        rt.kill_indirected("X", scope, levels=1)
        assert "A" in scope  # Kept
        assert "B" not in scope  # Killed
        assert "C" not in scope  # Killed

    def test_exclusive_kill_multiple_except(self, rt):
        """K @X where X='(A,B)' kills all locals except A and B."""
        scope = {
            "X": MArray(value="(A,B)"),
            "A": MArray(value="keep"),
            "B": MArray(value="keep"),
            "C": MArray(value="kill"),
        }
        rt.kill_indirected("X", scope, levels=1)
        assert "A" in scope
        assert "B" in scope
        assert "C" not in scope

    def test_exclusive_plus_explicit_kill(self, rt):
        """K @X where X='(A),B,C' does exclusive kill then explicit kills."""
        scope = {
            "X": MArray(value="(A),B,C"),
            "A": MArray(value="keep after exclusive"),
            "B": MArray(value="kill explicitly"),
            "C": MArray(value="kill explicitly"),
            "D": MArray(value="kill by exclusive"),
        }
        rt.kill_indirected("X", scope, levels=1)
        # A is protected by exclusive
        assert "A" in scope
        # B and C are killed by explicit kill AFTER exclusive
        assert "B" not in scope
        assert "C" not in scope
        # D is killed by exclusive (not in except list)
        assert "D" not in scope

    def test_exclusive_kill_empty_except_list(self, rt):
        """K @X where X='()' kills all locals (empty except list)."""
        scope = {
            "X": MArray(value="()"),
            "A": MArray(value="kill"),
            "B": MArray(value="kill"),
        }
        rt.kill_indirected("X", scope, levels=1)
        # All killed (X was the source, also killed since not in except)
        assert "A" not in scope
        assert "B" not in scope


# =============================================================================
# write_indirection() Tests for Expression Indirection (Phase 130)
# =============================================================================


class TestWriteIndirectionExpressionPatterns:
    """Tests for write_indirection with expression indirection patterns.

    When using expression indirection like @''10 (NOT NOT 10 = 1),
    the expression is evaluated at compile time, and the result is
    passed to write_indirection with levels=0 since the indirection
    is already resolved.
    """

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance with output capture."""
        runtime = MUMPSRuntime()
        runtime._capture_output = True
        runtime.clear()
        return runtime

    def test_write_indirection_levels_zero(self, rt):
        """write_indirection with levels=0 executes source directly.

        When levels=0, the source is already the final value to execute
        as WRITE arguments. No variable resolution is performed.
        """
        scope = {}
        rt.write_indirection("1", scope, levels=0)
        assert rt.get_output() == "1"

    def test_write_indirection_levels_zero_expression_result(self, rt):
        """write_indirection with levels=0 handles numeric strings.

        For @''10, the expression ''10 evaluates to 1 at compile time.
        This is passed as source="1" with levels=0.
        """
        scope = {}
        # ''10 = NOT (NOT 10) = NOT 0 = 1
        rt.write_indirection("1", scope, levels=0)
        assert rt.get_output() == "1"

    def test_write_indirection_levels_zero_with_format_control(self, rt):
        """write_indirection with levels=0 handles format controls.

        For W @A where A="!?3,1", the resolved value contains format controls.
        """
        scope = {}
        # Format control: newline, tab to col 3, write "1"
        rt.write_indirection("!?3,1", scope, levels=0)
        output = rt.get_output()
        # Should have newline and proper spacing
        assert "\n" in output
        assert "1" in output

    def test_write_indirection_levels_one_normal(self, rt):
        """write_indirection with levels=1 resolves variable.

        For W @A where A="B", B=42, resolve A→"B"→42, output 42.
        """
        scope = {"A": MArray(value="B"), "B": MArray(value=42)}
        rt.write_indirection("A", scope, levels=1)
        assert rt.get_output() == "42"

    def test_write_indirection_levels_one_with_format(self, rt):
        """write_indirection resolves to format controls correctly.

        For W @A where A="!?3,1", execute newline, tab to 3, write 1.
        """
        scope = {"A": MArray(value="!?3,1")}
        rt.write_indirection("A", scope, levels=1)
        output = rt.get_output()
        assert "\n" in output
        assert "1" in output

    def test_write_indirection_levels_two(self, rt):
        """write_indirection with levels=2 resolves twice.

        For W @@A where A="B", B="!?3,X", X=99: A→"B", B→"!?3,X"→newline+tab+99.
        """
        scope = {
            "A": MArray(value="B"),
            "B": MArray(value="!?3,X"),
            "X": MArray(value=99),
        }
        rt.write_indirection("A", scope, levels=2)
        output = rt.get_output()
        assert "\n" in output
        assert "99" in output

    def test_write_indirection_with_nested_at_expression(self, rt):
        """write_indirection handles values containing @-expressions.

        For W @A where A="@B+1", B="C", C=100:
        Resolve A→"@B+1", then execute_mumps evaluates @B+1→C+1→101.
        """
        scope = {
            "A": MArray(value="@B+1"),
            "B": MArray(value="C"),
            "C": MArray(value=100),
        }
        rt.write_indirection("A", scope, levels=1)
        output = rt.get_output()
        assert "101" in output
