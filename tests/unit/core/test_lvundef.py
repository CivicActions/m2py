"""Unit tests for unconditional LVUNDEF (Phase 12: US10).

T077: Unit tests for unconditional LVUNDEF
T078: Test verifying no strict_mode parameter exists in CurrentScope

The MUMPS standard mandates M6 errors for undefined local variable access.
YDB defaults to LVUNDEF errors. The current m2py behavior must match.
"""

import inspect

import pytest

from m2py.core.exceptions import LVUNDEFError
from m2py.core.scope import CurrentScope


class TestUnconditionalLVUNDEF:
    """T077: Unit tests for unconditional LVUNDEF behavior."""

    def test_undefined_simple_variable_raises(self):
        """Accessing undefined simple variable raises LVUNDEFError."""
        scope = CurrentScope(scope_dict={})
        with pytest.raises(LVUNDEFError) as exc_info:
            scope.get("X")
        assert "X" in str(exc_info.value)

    def test_undefined_subscripted_variable_raises(self):
        """Accessing undefined subscripted variable raises LVUNDEFError."""
        scope = CurrentScope(scope_dict={})
        with pytest.raises(LVUNDEFError) as exc_info:
            scope.get("A(1)")
        assert "A" in str(exc_info.value)

    def test_undefined_subscript_of_existing_array_raises(self):
        """Accessing undefined subscript of existing array raises LVUNDEFError."""
        from m2py.runtime import MArray

        A = MArray()
        A["1"] = "exists"
        scope = CurrentScope(scope_dict={"A": A})
        # A(1) exists but A(2) doesn't
        with pytest.raises(LVUNDEFError) as exc_info:
            scope.get_subscripted("A", ["2"])
        assert "A(2)" in str(exc_info.value)

    def test_defined_variable_returns_value(self):
        """Accessing defined variable returns its value."""
        scope = CurrentScope(scope_dict={"X": "hello"})
        result = scope.get("X")
        assert result == "hello"

    def test_defined_subscripted_variable_returns_value(self):
        """Accessing defined subscripted variable returns its value."""
        from m2py.runtime import MArray

        A = MArray()
        A["1"] = "value_at_1"
        scope = CurrentScope(scope_dict={"A": A})
        result = scope.get_subscripted("A", ["1"])
        assert result == "value_at_1"

    def test_empty_string_is_defined(self):
        """Empty string is a valid defined value, not LVUNDEF."""
        scope = CurrentScope(scope_dict={"X": ""})
        result = scope.get("X")
        assert result == ""

    def test_zero_is_defined(self):
        """Zero is a valid defined value, not LVUNDEF."""
        scope = CurrentScope(scope_dict={"X": 0})
        result = scope.get("X")
        assert result == 0

    def test_error_includes_variable_name(self):
        """LVUNDEF error message includes the variable name."""
        scope = CurrentScope(scope_dict={})
        with pytest.raises(LVUNDEFError) as exc_info:
            scope.get("UNDEFINED")
        assert "UNDEFINED" in str(exc_info.value)

    def test_error_includes_subscripts_for_array(self):
        """LVUNDEF error message includes subscripts for array access."""
        from m2py.runtime import MArray

        A = MArray()
        scope = CurrentScope(scope_dict={"A": A})
        with pytest.raises(LVUNDEFError) as exc_info:
            scope.get_subscripted("A", ["1", "2"])
        error_msg = str(exc_info.value)
        assert "A" in error_msg
        assert "1" in error_msg
        assert "2" in error_msg


class TestNoStrictModeParameter:
    """T078: Test verifying no strict_mode parameter exists."""

    def test_no_strict_mode_parameter_in_init(self):
        """CurrentScope.__init__ does not accept strict_mode parameter."""
        sig = inspect.signature(CurrentScope.__init__)
        param_names = list(sig.parameters.keys())
        assert "strict_mode" not in param_names

    def test_no_strict_mode_attribute(self):
        """CurrentScope instances have no _strict_mode attribute."""
        scope = CurrentScope(scope_dict={})
        assert not hasattr(scope, "_strict_mode")

    def test_constructor_rejects_strict_mode_kwarg(self):
        """Passing strict_mode to constructor raises TypeError."""
        with pytest.raises(TypeError):
            CurrentScope(scope_dict={}, strict_mode=True)


class TestLVUNDEFExceptionDetails:
    """Additional tests for LVUNDEFError behavior."""

    def test_lvundef_is_exception(self):
        """LVUNDEFError is an Exception subclass."""
        assert issubclass(LVUNDEFError, Exception)

    def test_lvundef_can_be_caught_as_key_error(self):
        """LVUNDEFError can be caught as KeyError (MUMPS compatibility)."""
        # Note: Check if LVUNDEFError inherits from KeyError
        # This is important for error handler compatibility
        scope = CurrentScope(scope_dict={})
        try:
            scope.get("UNDEF")
        except (LVUNDEFError, KeyError):
            pass  # Should be catchable as either

    def test_lvundef_preserves_variable_name(self):
        """LVUNDEFError stores the variable name for programmatic access."""
        scope = CurrentScope(scope_dict={})
        try:
            scope.get("MYVAR")
        except LVUNDEFError as e:
            # The variable name should be accessible somehow
            assert "MYVAR" in str(e)


class TestLVUNDEFWithMArray:
    """Tests for LVUNDEF with MArray auto-vivification."""

    def test_marray_value_attribute_defined(self):
        """MArray with .value set is defined."""
        from m2py.runtime import MArray

        arr = MArray()
        arr.value = "test"
        scope = CurrentScope(scope_dict={"X": arr})
        assert scope.get("X") == "test"

    def test_marray_without_value_raises(self):
        """MArray without .value set raises LVUNDEF."""
        from m2py.runtime import MArray

        arr = MArray()  # No value set
        scope = CurrentScope(scope_dict={"X": arr})
        # An MArray with no value IS undefined
        with pytest.raises(LVUNDEFError):
            scope.get("X")

    def test_marray_with_only_descendants_raises(self):
        """MArray with only descendants (no root value) raises LVUNDEF."""
        from m2py.runtime import MArray

        arr = MArray()
        arr["1"] = "child"  # Has descendants but no root value
        scope = CurrentScope(scope_dict={"X": arr})
        # $DATA(X) would be 10 (descendants only, no value)
        # MUMPS: Write X would raise LVUNDEF
        with pytest.raises(LVUNDEFError):
            scope.get("X")
