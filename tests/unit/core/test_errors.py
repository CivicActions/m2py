"""Unit tests for LVUNDEF error handling.

Tests the strict mode LVUNDEF error detection in CurrentScope.

Feature: 018-unified-variable-system
Requirements: FR-025 (LVUNDEF error)
Tasks: T036e, T036f
"""

import pytest

from m2py.core.exceptions import LVUNDEFError
from m2py.core.scope import CurrentScope


class TestLVUNDEFBasic:
    """Basic LVUNDEF error tests."""

    def test_strict_mode_raises_on_undefined_simple(self):
        """Accessing undefined variable in strict mode raises LVUNDEF."""
        scope = CurrentScope(scope_dict={}, strict_mode=True)

        with pytest.raises(LVUNDEFError) as exc_info:
            scope.get("UNDEFINED")

        assert "UNDEFINED" in str(exc_info.value)
        assert exc_info.value.name == "UNDEFINED"

    def test_strict_mode_off_returns_empty_string(self):
        """Accessing undefined variable without strict mode returns empty string."""
        scope = CurrentScope(scope_dict={}, strict_mode=False)

        result = scope.get("UNDEFINED")
        assert result == ""

    def test_defined_variable_works_in_strict_mode(self):
        """Defined variable works normally in strict mode."""
        scope = CurrentScope(scope_dict={"X": 42}, strict_mode=True)

        result = scope.get("X")
        assert result == 42

    def test_strict_mode_default_is_false(self):
        """Default strict_mode is False (permissive)."""
        scope = CurrentScope(scope_dict={})
        # Should not raise
        result = scope.get("NOTDEFINED")
        assert result == ""


class TestLVUNDEFSubscripted:
    """LVUNDEF tests for subscripted variables."""

    def test_strict_mode_undefined_base_raises(self):
        """Accessing A(1) when A is undefined raises LVUNDEF in strict mode."""
        scope = CurrentScope(scope_dict={}, strict_mode=True)

        with pytest.raises(LVUNDEFError) as exc_info:
            scope.get_subscripted("A", [1])

        assert "A(1)" in str(exc_info.value)

    def test_strict_mode_undefined_subscript_raises(self):
        """Accessing A(1,2) when A(1,2) doesn't exist raises LVUNDEF."""
        from m2py.runtime import MArray

        A = MArray()
        A["1"] = "exists"  # A(1) exists, but A(1,2) does not
        scope = CurrentScope(scope_dict={"A": A}, strict_mode=True)

        # A(1) works
        result = scope.get_subscripted("A", ["1"])
        assert result == "exists"

        # A(1,2) raises LVUNDEF
        with pytest.raises(LVUNDEFError) as exc_info:
            scope.get_subscripted("A", ["1", "2"])

        assert "A(1,2)" in str(exc_info.value)

    def test_strict_mode_string_form_subscripted(self):
        """LVUNDEF works with string form 'A(1,2)' in strict mode."""
        scope = CurrentScope(scope_dict={}, strict_mode=True)

        with pytest.raises(LVUNDEFError) as exc_info:
            scope.get("A(1,2)")

        assert "A" in str(exc_info.value)


class TestLVUNDEFPercentVariables:
    """LVUNDEF tests for % prefix variables."""

    def test_percent_variable_undefined_strict(self):
        """% prefix undefined variable raises LVUNDEF."""
        scope = CurrentScope(scope_dict={}, strict_mode=True)

        with pytest.raises(LVUNDEFError) as exc_info:
            scope.get("%UNDEFINED")

        assert "%UNDEFINED" in str(exc_info.value)

    def test_percent_variable_defined_works(self):
        """Defined % variable works in strict mode."""
        scope = CurrentScope(scope_dict={}, strict_mode=True)
        scope.set("%VAR", 100)

        result = scope.get("%VAR")
        assert result == 100


class TestLVUNDEFEdgeCases:
    """Edge cases for LVUNDEF error handling."""

    def test_empty_string_value_not_undefined(self):
        """Variable set to empty string is NOT undefined."""
        scope = CurrentScope(scope_dict={"X": ""}, strict_mode=True)

        # Should NOT raise - X is defined with value ""
        result = scope.get("X")
        assert result == ""

    def test_zero_value_not_undefined(self):
        """Variable set to 0 is NOT undefined."""
        scope = CurrentScope(scope_dict={"X": 0}, strict_mode=True)

        # Should NOT raise - X is defined with value 0
        result = scope.get("X")
        assert result == 0

    def test_none_value_not_undefined(self):
        """Variable set to None is NOT undefined (edge case)."""
        scope = CurrentScope(scope_dict={"X": None}, strict_mode=True)

        # Should NOT raise - X is defined (even though value is None)
        # In MUMPS, explicitly setting a variable to anything means it's defined
        result = scope.get("X")
        # _extract_value converts None to ""
        assert result == ""

    def test_custom_default_ignored_in_strict_mode(self):
        """Custom default is ignored when LVUNDEF is raised."""
        scope = CurrentScope(scope_dict={}, strict_mode=True)

        # Even with default=42, should raise LVUNDEF
        with pytest.raises(LVUNDEFError):
            scope.get("UNDEFINED", default=42)


class TestLVUNDEFMArrayIntegration:
    """LVUNDEF tests with MArray objects."""

    def test_marray_undefined_subscript_strict(self):
        """Accessing non-existent MArray subscript raises LVUNDEF."""
        from m2py.runtime import MArray

        A = MArray()
        A["1"]["2"] = "val"
        scope = CurrentScope(scope_dict={"A": A}, strict_mode=True)

        # A(1,2) exists
        assert scope.get_subscripted("A", ["1", "2"]) == "val"

        # A(1,3) does not exist
        with pytest.raises(LVUNDEFError) as exc_info:
            scope.get_subscripted("A", ["1", "3"])

        assert "A(1,3)" in str(exc_info.value)

    def test_marray_node_without_value_raises_lvundef(self):
        """MArray node with descendants but no value raises LVUNDEF in strict mode.

        If A(1) has no value but A(1,2) does (i.e., $D(A(1))=10),
        accessing A(1) should raise LVUNDEF because there's no value.
        """
        from m2py.runtime import MArray

        A = MArray()
        # Set A(1,2) without setting A(1) directly
        A["1"]["2"] = "child_value"
        # A(1) now has descendants but no own value ($D=10)
        scope = CurrentScope(scope_dict={"A": A}, strict_mode=True)

        # Accessing A(1,2) works (has value, $D=1)
        assert scope.get_subscripted("A", ["1", "2"]) == "child_value"

        # Accessing A(1) should raise LVUNDEF in strict mode
        # because $D(A(1))=10 means no value (only descendants)
        with pytest.raises(LVUNDEFError) as exc_info:
            scope.get_subscripted("A", ["1"])

        assert "A(1)" in str(exc_info.value)

    def test_marray_node_without_value_returns_empty_non_strict(self):
        """MArray node with descendants but no value returns '' in non-strict mode."""
        from m2py.runtime import MArray

        A = MArray()
        A["1"]["2"] = "child_value"
        # Non-strict mode (default)
        scope = CurrentScope(scope_dict={"A": A}, strict_mode=False)

        # A(1) has no value but has descendants - returns "" in non-strict mode
        result = scope.get_subscripted("A", ["1"])
        assert result == ""


class TestLVUNDEFErrorMessage:
    """Tests for LVUNDEF error message formatting."""

    def test_error_message_format(self):
        """LVUNDEF error message follows expected format."""
        scope = CurrentScope(scope_dict={}, strict_mode=True)

        with pytest.raises(LVUNDEFError) as exc_info:
            scope.get("MYVAR")

        error = exc_info.value
        assert error.name == "MYVAR"
        assert "LVUNDEF" in error.message
        assert "MYVAR" in error.message

    def test_subscripted_error_message(self):
        """LVUNDEF error message includes subscripts."""
        scope = CurrentScope(scope_dict={}, strict_mode=True)

        with pytest.raises(LVUNDEFError) as exc_info:
            scope.get("DATA(1,2,3)")

        error = exc_info.value
        # The error should mention DATA with subscripts
        assert "DATA" in error.message
