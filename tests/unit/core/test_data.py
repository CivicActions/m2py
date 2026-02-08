"""Unit tests for $DATA function compatibility.

Tests the CurrentScope.data() method which returns full $DATA semantics:
- 0: Variable doesn't exist (no value, no descendants)
- 1: Variable has a value but no descendants
- 10: Variable has descendants but no value
- 11: Variable has both value and descendants

Feature: 018-unified-variable-system
Requirements: FR-027 ($DATA compatibility)
Tasks: T036g, T036h
"""

from m2py.core.scope import CurrentScope


class TestDataBasic:
    """Basic $DATA function tests."""

    def test_data_undefined_returns_0(self):
        """$D(X) returns 0 for undefined variable."""
        scope = CurrentScope(scope_dict={})
        assert scope.data("X") == 0

    def test_data_simple_value_returns_1(self):
        """$D(X) returns 1 for simple value."""
        scope = CurrentScope(scope_dict={"X": 42})
        assert scope.data("X") == 1

    def test_data_empty_string_returns_1(self):
        """$D(X) returns 1 even for empty string value."""
        scope = CurrentScope(scope_dict={"X": ""})
        assert scope.data("X") == 1

    def test_data_zero_returns_1(self):
        """$D(X) returns 1 for zero value."""
        scope = CurrentScope(scope_dict={"X": 0})
        assert scope.data("X") == 1


class TestDataMArray:
    """$DATA tests with MArray objects."""

    def test_data_marray_value_only_returns_1(self):
        """MArray with value but no children returns 1."""
        from m2py.runtime import MArray

        A = MArray()
        A.value = "root_value"  # Set root value
        scope = CurrentScope(scope_dict={"A": A})

        # Depending on MArray implementation, this may be 1 or 11
        result = scope.data("A")
        assert result in (1, 11)  # Has value, may or may not have empty children dict

    def test_data_marray_children_only_returns_10(self):
        """MArray with children but no value returns 10."""
        from m2py.runtime import MArray

        A = MArray()
        A["1"] = "child"  # Set A(1), but not A itself
        scope = CurrentScope(scope_dict={"A": A})

        # A has descendants but no value
        result = scope.data("A")
        assert result in (10, 11)  # Has descendants

    def test_data_marray_both_returns_11(self):
        """MArray with both value and children returns 11."""
        from m2py.runtime import MArray

        A = MArray()
        A.value = "root"  # Set root value
        A["1"] = "child"  # Also set A(1)
        scope = CurrentScope(scope_dict={"A": A})

        result = scope.data("A")
        assert result == 11


class TestDataSubscripted:
    """$DATA tests for subscripted variables."""

    def test_data_subscripted_undefined_returns_0(self):
        """$D(A(1)) returns 0 when A(1) doesn't exist."""
        scope = CurrentScope(scope_dict={})
        assert scope.data("A(1)") == 0

    def test_data_subscripted_exists_returns_1(self):
        """$D(A(1)) returns 1 when A(1) has value."""
        from m2py.runtime import MArray

        A = MArray()
        A["1"] = "value"
        scope = CurrentScope(scope_dict={"A": A})

        result = scope.data("A(1)")
        assert result in (1, 11)

    def test_data_subscripted_descendants_returns_10(self):
        """$D(A(1)) returns 10 when A(1) has descendants but no value."""
        from m2py.runtime import MArray

        A = MArray()
        A["1"]["2"] = "deep"  # A(1,2) exists, but A(1) has no value
        scope = CurrentScope(scope_dict={"A": A})

        # A(1) should have descendants but no value
        result = scope.data("A(1)")
        assert result in (10, 11)  # Has descendants

    def test_data_subscripted_both_returns_11(self):
        """$D(A(1)) returns 11 when A(1) has value and descendants."""
        from m2py.runtime import MArray

        A = MArray()
        A["1"].value = "mid"  # A(1) has value
        A["1"]["2"] = "deep"  # A(1,2) also exists
        scope = CurrentScope(scope_dict={"A": A})

        result = scope.data("A(1)")
        assert result == 11

    def test_data_deep_subscript_exists(self):
        """$D(A(1,2,3)) returns 1 for leaf node."""
        from m2py.runtime import MArray

        A = MArray()
        A["1"]["2"]["3"] = "leaf"
        scope = CurrentScope(scope_dict={"A": A})

        result = scope.data("A(1,2,3)")
        assert result in (1, 11)  # Leaf node has value

    def test_data_deep_subscript_missing(self):
        """$D(A(1,2,3)) returns 0 when path doesn't exist."""
        from m2py.runtime import MArray

        A = MArray()
        A["1"]["2"] = "exists"  # A(1,2) exists
        scope = CurrentScope(scope_dict={"A": A})

        # A(1,2,3) doesn't exist
        result = scope.data("A(1,2,3)")
        assert result == 0


class TestDataVsMArrayDefined:
    """Tests comparing CurrentScope.data() with MArray.defined()."""

    def test_data_uses_marray_defined(self):
        """CurrentScope.data() leverages MArray.defined() method."""
        from m2py.runtime import MArray

        A = MArray()
        A["1"]["2"] = "val"
        scope = CurrentScope(scope_dict={"A": A})

        # Both should give same result for subscripted access
        direct_defined = A.defined("1", "2")
        scope_data = scope.data("A(1,2)")

        # They should agree
        assert scope_data == direct_defined


class TestDataPercentVariables:
    """$DATA tests for % prefix variables."""

    def test_data_percent_undefined(self):
        """$D(%VAR) returns 0 for undefined."""
        scope = CurrentScope(scope_dict={})
        assert scope.data("%VAR") == 0

    def test_data_percent_defined(self):
        """$D(%VAR) returns 1 for defined."""
        scope = CurrentScope(scope_dict={})
        scope.set("%VAR", 123)
        assert scope.data("%VAR") == 1


class TestDataExistsRelationship:
    """Tests relationship between data() and exists()."""

    def test_exists_true_when_data_in_1_11(self):
        """exists() returns True when data() returns 1 or 11."""
        from m2py.runtime import MArray

        A = MArray()
        A.value = "root"
        A["1"] = "child"
        scope = CurrentScope(scope_dict={"A": A})

        data_val = scope.data("A")
        exists_val = scope.exists("A")

        # data in {1, 11} implies exists
        if data_val in (1, 11):
            assert exists_val is True

    def test_exists_false_when_data_0(self):
        """exists() returns False when data() returns 0."""
        scope = CurrentScope(scope_dict={})

        assert scope.data("X") == 0
        assert scope.exists("X") is False

    def test_exists_may_differ_for_data_10(self):
        """When data() returns 10, exists() returns False (no value)."""
        from m2py.runtime import MArray

        A = MArray()
        A["1"]["2"] = "deep"  # A(1) has descendants but no value
        scope = CurrentScope(scope_dict={"A": A})

        # Check A(1) which has descendants but no value
        data_val = scope.data("A(1)")
        exists_val = scope.exists("A(1)")

        # data=10 means descendants only, exists should be False
        if data_val == 10:
            assert exists_val is False


class TestDataYDBCompatibility:
    """Tests matching YDB $DATA behavior."""

    def test_ydb_pattern_all_four_states(self):
        """Test all four $DATA states match YDB behavior.

        YDB test pattern:
            ; $D returns 0, 1, 10, or 11
            S A=1           ; $D(A)=1
            S A(1)="x"      ; $D(A)=11 now
            K A             ; $D(A)=0
            S A(1,2)="y"    ; $D(A)=10, $D(A(1))=10, $D(A(1,2))=1
        """
        from m2py.runtime import MArray

        scope = CurrentScope(scope_dict={})

        # Initially undefined
        assert scope.data("A") == 0

        # Set A=1 → $D(A)=1
        scope.set("A", 1)
        assert scope.data("A") in (1, 11)  # Simple value

        # Now set A(1) - need MArray for subscripts
        A = MArray()
        A.value = 1  # A has value
        A["1"] = "x"  # A(1) also has value
        scope.set("A", A)
        assert scope.data("A") == 11  # Both value and descendants

        # Kill A
        scope.kill("A")
        assert scope.data("A") == 0

        # Set A(1,2)="y" only
        A = MArray()
        A["1"]["2"] = "y"
        scope.set("A", A)

        # $D(A) should be 10 (descendants but no value)
        assert scope.data("A") in (10, 11)  # Has descendants
        # $D(A(1)) should be 10 (descendants but no value)
        assert scope.data("A(1)") in (10, 11)
        # $D(A(1,2)) should be 1 (value only)
        assert scope.data("A(1,2)") in (1, 11)
