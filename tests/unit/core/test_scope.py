"""Unit tests for CurrentScope.

Tests the unified variable access abstraction per
contracts/current-scope.md.

Feature: 018-unified-variable-system
Requirements: FR-036, FR-037, FR-038
"""

from m2py.core.scope import CurrentScope


class TestBasicGetSet:
    """Tests for basic get/set operations."""

    def test_set_and_get_simple(self):
        """Basic set and get of a simple variable."""
        scope = CurrentScope(scope_dict={})
        scope.set("X", 5)
        assert scope.get("X") == 5

    def test_get_undefined_returns_empty_string(self):
        """Undefined variables return empty string (MUMPS behavior)."""
        scope = CurrentScope(scope_dict={})
        assert scope.get("Y") == ""

    def test_get_with_custom_default(self):
        """Get with custom default value."""
        scope = CurrentScope(scope_dict={})
        assert scope.get("Z", default=42) == 42

    def test_set_overwrites(self):
        """Setting a variable overwrites previous value."""
        scope = CurrentScope(scope_dict={})
        scope.set("X", 1)
        scope.set("X", 2)
        assert scope.get("X") == 2

    def test_various_value_types(self):
        """Can store various value types."""
        scope = CurrentScope(scope_dict={})
        scope.set("A", 42)
        scope.set("B", "hello")
        scope.set("C", 3.14)
        scope.set("D", [1, 2, 3])

        assert scope.get("A") == 42
        assert scope.get("B") == "hello"
        assert scope.get("C") == 3.14
        assert scope.get("D") == [1, 2, 3]


class TestNameTranslation:
    """Tests for MUMPS to Python name translation."""

    def test_percent_prefix(self):
        """% prefix variables are properly translated."""
        scope = CurrentScope(scope_dict={})
        scope.set("%FOO", 42)
        assert scope.get("%FOO") == 42

        # Verify internal storage uses translated name
        assert "_pct_FOO" in scope._scope_dict

    def test_regular_names_unchanged(self):
        """Regular MUMPS names stay the same."""
        scope = CurrentScope(scope_dict={})
        scope.set("VCOMP", 100)
        assert scope.get("VCOMP") == 100
        assert "VCOMP" in scope._scope_dict


class TestMumpsNameVsPythonNameLookup:
    """Tests for MUMPS name lookup when storage uses MUMPS names directly.

    Feature: 017-ydb-test-failures Phase 19 (V4QSUB fix)

    Some generated code stores variables using MUMPS names (e.g., "%2")
    while other code uses Python-translated names (e.g., "_pct_2").
    The _lookup() method must try both to handle mixed conventions.
    """

    def test_lookup_mumps_name_directly_stored(self):
        """Get works when variable stored with MUMPS name directly.

        This is the V4QSUB pattern: extrinsic function parameters like %2
        are stored as _scope["%2"] = MArray(value=x), but generated code
        tries to look them up via get("%2").
        """
        from m2py.runtime import MArray

        # Simulate generated code that stores with MUMPS name directly
        scope_dict = {"%2": MArray(value="hello")}
        scope = CurrentScope(scope_dict=scope_dict)

        # Should find it even though no Python-translated entry exists
        assert scope.get("%2") == "hello"

    def test_lookup_python_name_stored(self):
        """Get works when variable stored with Python name."""

        # Store with Python name (via set which translates)
        scope = CurrentScope(scope_dict={})
        scope.set("%FOO", "bar")

        # Should find via either name
        assert scope.get("%FOO") == "bar"

    def test_lookup_mixed_storage_conventions(self):
        """Get works with mixed MUMPS and Python name storage.

        Real-world generated code may have some variables stored with
        MUMPS names and others with Python names.
        """
        from m2py.runtime import MArray

        scope_dict = {
            "%1": MArray(value="first"),  # MUMPS name
            "_pct_2": MArray(value="second"),  # Python name
            "REGULAR": MArray(value="normal"),  # Same either way
        }
        scope = CurrentScope(scope_dict=scope_dict)

        # All should be accessible
        assert scope.get("%1") == "first"
        assert scope.get("%2") == "second"
        assert scope.get("REGULAR") == "normal"

    def test_mumps_name_takes_precedence(self):
        """When both MUMPS and Python names exist, MUMPS name is used.

        This ensures consistency - if code stores with MUMPS name, that
        value is returned even if a Python-named entry also exists.
        """
        from m2py.runtime import MArray

        scope_dict = {
            "%X": MArray(value="mumps_value"),
            "_pct_X": MArray(value="python_value"),
        }
        scope = CurrentScope(scope_dict=scope_dict)

        # MUMPS name should take precedence
        assert scope.get("%X") == "mumps_value"

    def test_exists_with_mumps_name(self):
        """exists() works with MUMPS names stored directly."""
        from m2py.runtime import MArray

        scope_dict = {"%VAR": MArray(value=42)}
        scope = CurrentScope(scope_dict=scope_dict)

        assert scope.exists("%VAR") is True
        assert scope.exists("%UNDEF") is False

    def test_data_with_mumps_name(self):
        """data() works with MUMPS names stored directly."""
        from m2py.runtime import MArray

        scope_dict = {"%VAR": MArray(value=42)}
        scope = CurrentScope(scope_dict=scope_dict)

        assert scope.data("%VAR") == 1  # Has value, no descendants
        assert scope.data("%UNDEF") == 0  # Undefined


class TestSubscriptedAccess:
    """Tests for subscripted variable access."""

    def test_set_and_get_subscripted(self):
        """Set and get subscripted variables."""
        scope = CurrentScope(scope_dict={})
        scope.set_subscripted("A", [1, 2], "hello")
        assert scope.get_subscripted("A", [1, 2]) == "hello"

    def test_get_string_form_subscripted(self):
        """Get using string form like 'A(1,2)'."""
        scope = CurrentScope(scope_dict={})
        scope.set_subscripted("A", [1, 2], "hello")
        assert scope.get("A(1,2)") == "hello"

    def test_set_string_form_subscripted(self):
        """Set using string form like 'A(1,2)'."""
        scope = CurrentScope(scope_dict={})
        scope.set("A(1,2)", "hello")
        assert scope.get_subscripted("A", ["1", "2"]) == "hello"

    def test_undefined_subscript_returns_default(self):
        """Undefined subscripted variable returns default."""
        scope = CurrentScope(scope_dict={})
        assert scope.get_subscripted("A", [1, 2]) == ""
        assert scope.get("A(1,2)") == ""

    def test_nested_subscripts(self):
        """Multiple levels of subscripts."""
        scope = CurrentScope(scope_dict={})
        scope.set_subscripted("A", [1], "a1")
        scope.set_subscripted("A", [1, 1], "a11")
        scope.set_subscripted("A", [1, 2], "a12")
        scope.set_subscripted("A", [2], "a2")

        assert scope.get_subscripted("A", [1]) == "a1"
        assert scope.get_subscripted("A", [1, 1]) == "a11"
        assert scope.get_subscripted("A", [1, 2]) == "a12"
        assert scope.get_subscripted("A", [2]) == "a2"


class TestMArrayValueExtraction:
    """Tests for FR-038: MArray .value extraction."""

    def test_extracts_value_attribute(self):
        """Objects with .value have value extracted."""

        class MockMArray:
            def __init__(self, v):
                self.value = v

        scope = CurrentScope(scope_dict={})
        arr = MockMArray("test")
        scope.set("M", arr)
        assert scope.get("M") == "test"

    def test_recursive_value_extraction(self):
        """Nested .value attributes are recursively extracted."""

        class MockMArray:
            def __init__(self, v):
                self.value = v

        scope = CurrentScope(scope_dict={})
        inner = MockMArray("final")
        outer = MockMArray(inner)
        scope.set("N", outer)
        assert scope.get("N") == "final"

    def test_none_becomes_empty_string(self):
        """None values become empty string (MUMPS undefined)."""
        scope = CurrentScope(scope_dict={"X": None})
        assert scope.get("X") == ""


class TestExists:
    """Tests for exists() method."""

    def test_exists_simple(self):
        """Exists returns True for defined variable."""
        scope = CurrentScope(scope_dict={})
        scope.set("X", "value")
        assert scope.exists("X")

    def test_not_exists(self):
        """Exists returns False for undefined variable."""
        scope = CurrentScope(scope_dict={})
        assert not scope.exists("Y")

    def test_exists_subscripted(self):
        """Exists works with subscripted variables."""
        scope = CurrentScope(scope_dict={})
        scope.set_subscripted("A", [1, 2], "hello")

        assert scope.exists("A(1,2)")
        assert not scope.exists("A(1,3)")
        assert not scope.exists("A(2)")


class TestIsDefined:
    """Tests for is_defined() method.

    Feature: 017-ydb-test-failures (indirection undefined check)

    is_defined() checks if a variable has a value at a specific location,
    similar to $DATA returning 1 or 11 (has value) vs 0 or 10 (no value).
    """

    def test_is_defined_simple_variable(self):
        """is_defined returns True for defined simple variable."""
        scope = CurrentScope(scope_dict={})
        scope.set("X", "value")
        assert scope.is_defined("X") is True

    def test_is_defined_undefined_variable(self):
        """is_defined returns False for undefined variable."""
        scope = CurrentScope(scope_dict={})
        assert scope.is_defined("UNDEF") is False

    def test_is_defined_subscripted_exists(self):
        """is_defined returns True for defined subscripted variable."""

        scope = CurrentScope(scope_dict={})
        scope.set_subscripted("A", [1, 2], "hello")
        assert scope.is_defined("A", subscripts=[1, 2]) is True

    def test_is_defined_subscripted_missing(self):
        """is_defined returns False for undefined subscripted location."""
        scope = CurrentScope(scope_dict={})
        scope.set_subscripted("A", [1, 2], "hello")
        assert scope.is_defined("A", subscripts=[1, 3]) is False
        assert scope.is_defined("A", subscripts=[2]) is False

    def test_is_defined_marray_with_value(self):
        """is_defined returns True for MArray with .value set."""
        from m2py.runtime import MArray

        arr = MArray()
        arr.value = "test"
        scope = CurrentScope(scope_dict={"X": arr})
        assert scope.is_defined("X") is True

    def test_is_defined_marray_without_value(self):
        """is_defined returns False for MArray with no .value (children only)."""
        from m2py.runtime import MArray

        arr = MArray()
        arr["child"] = "value"  # Only children, no top-level value
        scope = CurrentScope(scope_dict={"X": arr})
        # X has children but no value at X itself
        assert scope.is_defined("X") is False

    def test_is_defined_nested_marray_path(self):
        """is_defined navigates MArray subscripts correctly."""

        scope = CurrentScope(scope_dict={})
        scope.set_subscripted("A", [1], "first")
        scope.set_subscripted("A", [1, 2], "nested")

        assert scope.is_defined("A", subscripts=[1]) is True
        assert scope.is_defined("A", subscripts=[1, 2]) is True
        assert scope.is_defined("A", subscripts=[1, 3]) is False


class TestKill:
    """Tests for kill() method."""

    def test_kill_simple(self):
        """Kill removes a simple variable."""
        scope = CurrentScope(scope_dict={})
        scope.set("X", 5)
        assert scope.exists("X")

        scope.kill("X")
        assert not scope.exists("X")
        assert scope.get("X") == ""

    def test_kill_subscripted(self):
        """Kill subscripted variable removes that node."""
        scope = CurrentScope(scope_dict={})
        scope.set_subscripted("A", [1], "a1")
        scope.set_subscripted("A", [1, 1], "a11")
        scope.set_subscripted("A", [2], "a2")

        scope.kill("A(1)")

        assert not scope.exists("A(1)")
        # Note: In a real MArray, killing A(1) would also kill A(1,1)
        # This simple implementation doesn't fully model that
        assert scope.exists("A(2)")

    def test_kill_nonexistent(self):
        """Killing nonexistent variable is no-op."""
        scope = CurrentScope(scope_dict={})
        scope.kill("X")  # Should not raise


class TestFactoryMethod:
    """Tests for from_generated_context() factory."""

    def test_creates_from_scope(self):
        """Factory creates scope from _scope dict."""
        from m2py.runtime import MArray

        _scope = {"X": 5}
        cs = CurrentScope.from_generated_context(_scope)

        assert cs.get("X") == 5
        cs.set("Y", 10)
        # Value is wrapped in MArray for generated code compatibility
        assert isinstance(_scope["Y"], MArray)
        assert _scope["Y"].value == 10

    def test_creates_with_locals(self):
        """Factory accepts locals dict."""
        _scope = {}
        _locals = {"Z": 99}
        cs = CurrentScope.from_generated_context(_scope, _locals)

        # Scope is checked first, then locals
        assert cs.get("Z") == 99


class TestStoragePriority:
    """Tests for storage mechanism priority."""

    def test_scope_dict_priority(self):
        """scope_dict is checked before locals_dict."""
        scope_dict = {"X": "from_scope"}
        locals_dict = {"X": "from_locals"}

        cs = CurrentScope(scope_dict=scope_dict, locals_dict=locals_dict)
        assert cs.get("X") == "from_scope"

    def test_locals_dict_fallback(self):
        """locals_dict is checked when not in scope_dict."""
        scope_dict = {}
        locals_dict = {"Y": "from_locals"}

        cs = CurrentScope(scope_dict=scope_dict, locals_dict=locals_dict)
        assert cs.get("Y") == "from_locals"

    def test_set_uses_primary(self):
        """Set stores in primary (first non-None) storage."""
        from m2py.runtime import MArray

        scope_dict = {}
        locals_dict = {}

        cs = CurrentScope(scope_dict=scope_dict, locals_dict=locals_dict)
        cs.set("X", 42)

        # Value is wrapped in MArray for generated code compatibility
        assert isinstance(scope_dict["X"], MArray)
        assert scope_dict["X"].value == 42
        assert "X" not in locals_dict


class TestSubscriptParsing:
    """Tests for subscript name parsing."""

    def test_parse_no_subscripts(self):
        """Name without subscripts."""
        cs = CurrentScope(scope_dict={})
        base, subs = cs._parse_subscripted_name("X")
        assert base == "X"
        assert subs == []

    def test_parse_single_subscript(self):
        """Single subscript."""
        cs = CurrentScope(scope_dict={})
        base, subs = cs._parse_subscripted_name("A(1)")
        assert base == "A"
        assert subs == ["1"]

    def test_parse_multiple_subscripts(self):
        """Multiple subscripts."""
        cs = CurrentScope(scope_dict={})
        base, subs = cs._parse_subscripted_name("A(1,2,3)")
        assert base == "A"
        assert subs == ["1", "2", "3"]

    def test_parse_string_subscripts(self):
        """Subscripts with string content."""
        cs = CurrentScope(scope_dict={})
        base, subs = cs._parse_subscripted_name("A(foo,bar)")
        assert base == "A"
        assert subs == ["foo", "bar"]

    def test_parse_quoted_string_subscripts(self):
        """Quoted string subscripts have quotes stripped.

        Bug fix: B("key","sub") was returning ['\"key\"', '\"sub\"'] with quotes.
        Feature: 018-unified-variable-system
        """
        cs = CurrentScope(scope_dict={})
        base, subs = cs._parse_subscripted_name('B("key","sub")')
        assert base == "B"
        # Quotes should be stripped from the subscripts
        assert subs == ["key", "sub"]

    def test_parse_mixed_quoted_and_unquoted_subscripts(self):
        """Mixed quoted and unquoted subscripts."""
        cs = CurrentScope(scope_dict={})
        base, subs = cs._parse_subscripted_name('A(1,"two",3)')
        assert base == "A"
        assert subs == ["1", "two", "3"]

    def test_parse_subscript_with_escaped_quotes(self):
        """Subscript with escaped quotes inside string.

        MUMPS uses "" to escape quotes inside strings.
        """
        cs = CurrentScope(scope_dict={})
        # "he""llo" in MUMPS means he"llo
        base, subs = cs._parse_subscripted_name('A("he""llo")')
        assert base == "A"
        assert subs == ['he"llo']

    def test_parse_global_with_quoted_subscripts(self):
        """Global variable with quoted subscripts."""
        cs = CurrentScope(scope_dict={})
        base, subs = cs._parse_subscripted_name('^GLO("a","b")')
        assert base == "^GLO"
        assert subs == ["a", "b"]
