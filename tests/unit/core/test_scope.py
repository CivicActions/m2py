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
        _scope = {"X": 5}
        cs = CurrentScope.from_generated_context(_scope)

        assert cs.get("X") == 5
        cs.set("Y", 10)
        assert _scope["Y"] == 10

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
        scope_dict = {}
        locals_dict = {}

        cs = CurrentScope(scope_dict=scope_dict, locals_dict=locals_dict)
        cs.set("X", 42)

        assert scope_dict["X"] == 42
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
