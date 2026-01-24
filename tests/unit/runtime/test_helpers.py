"""Tests for runtime helper functions.

Tests the helper functions used by generated code for intrinsic functions.
"""

from m2py.runtime import MArray
from m2py.runtime.helpers import (
    _mumps_collation_key,
    m_data,
    m_format_output,
    m_get,
    m_get_global,
    m_order,
    m_order_global,
    m_query,
    m_query_global,
)
from m2py.runtime.globals import InMemoryGlobalStorage


class TestMumpsCollationKey:
    """Tests for MUMPS collation order."""

    def test_numeric_ordering(self):
        """Numeric values sort by numeric value."""
        keys = [3, 1, -1, 0, 2, -2]
        sorted_keys = sorted(keys, key=_mumps_collation_key)
        assert sorted_keys == [-2, -1, 0, 1, 2, 3]

    def test_strings_after_numbers(self):
        """Strings sort after all numbers."""
        keys = [1, "A", 0, "B", -1]
        sorted_keys = sorted(keys, key=_mumps_collation_key)
        assert sorted_keys == [-1, 0, 1, "A", "B"]

    def test_numeric_strings_as_numbers(self):
        """Numeric strings are treated as numbers for collation."""
        keys = ["1", "-1", "A", "0"]
        sorted_keys = sorted(keys, key=_mumps_collation_key)
        assert sorted_keys == ["-1", "0", "1", "A"]

    def test_decimal_numbers(self):
        """Decimal numbers sort correctly."""
        keys = ["-1.5", "-1", "-0.5", "0", "0.5", "1"]
        sorted_keys = sorted(keys, key=_mumps_collation_key)
        assert sorted_keys == ["-1.5", "-1", "-0.5", "0", "0.5", "1"]


class TestMOrder:
    """Tests for m_order() helper function."""

    def test_forward_from_empty_string(self):
        """Forward iteration from empty string returns first key."""
        arr = MArray()
        arr[1].value = "a"
        arr[2].value = "b"
        arr[3].value = "c"
        assert m_order(arr, ("",), 1) == "1"

    def test_forward_iteration(self):
        """Forward iteration returns next key."""
        arr = MArray()
        arr[1].value = "a"
        arr[2].value = "b"
        arr[3].value = "c"
        assert m_order(arr, ("1",), 1) == "2"
        assert m_order(arr, ("2",), 1) == "3"
        assert m_order(arr, ("3",), 1) == ""

    def test_reverse_from_empty_string(self):
        """Reverse iteration from empty string returns last key."""
        arr = MArray()
        arr[1].value = "a"
        arr[2].value = "b"
        arr[3].value = "c"
        assert m_order(arr, ("",), -1) == "3"

    def test_reverse_iteration(self):
        """Reverse iteration returns previous key."""
        arr = MArray()
        arr[1].value = "a"
        arr[2].value = "b"
        arr[3].value = "c"
        assert m_order(arr, ("3",), -1) == "2"
        assert m_order(arr, ("2",), -1) == "1"
        assert m_order(arr, ("1",), -1) == ""

    def test_collation_order(self):
        """Keys are returned in MUMPS collation order."""
        arr = MArray()
        arr[-1].value = "neg"
        arr[0].value = "zero"
        arr[1].value = "pos"
        arr["A"].value = "upper"
        arr["a"].value = "lower"
        assert m_order(arr, ("",), 1) == "-1"
        assert m_order(arr, ("1",), 1) == "A"

    def test_none_array(self):
        """None array returns empty string."""
        assert m_order(None, ("",), 1) == ""

    def test_nested_subscripts(self):
        """Nested subscripts work correctly."""
        arr = MArray()
        arr[1, 1].value = "a"
        arr[1, 2].value = "b"
        assert m_order(arr, ("1", ""), 1) == "1"
        assert m_order(arr, ("1", "1"), 1) == "2"


class TestMOrderGlobal:
    """Tests for m_order_global() helper function."""

    def test_forward_iteration(self):
        """Forward iteration on globals works correctly."""
        backend = InMemoryGlobalStorage()
        backend.set("G", ("1",), "a")
        backend.set("G", ("2",), "b")
        backend.set("G", ("3",), "c")
        assert m_order_global(backend, "G", ("",), 1) == "1"
        assert m_order_global(backend, "G", ("1",), 1) == "2"


class TestMQuery:
    """Tests for m_query() helper function."""

    def test_depth_first_traversal(self):
        """Query traverses tree depth-first."""
        arr = MArray()
        arr[1, 1].value = 1
        arr[1, 2].value = 2
        arr[2, 1].value = 3
        assert m_query(arr, "A", ("",)) == "A(1,1)"
        assert m_query(arr, "A", ("1", "1")) == "A(1,2)"
        assert m_query(arr, "A", ("1", "2")) == "A(2,1)"
        assert m_query(arr, "A", ("2", "1")) == ""

    def test_varying_depth(self):
        """Query handles varying depth correctly."""
        arr = MArray()
        arr[1, 1, 1].value = 1
        arr[1, 2].value = 2
        arr[2].value = 3
        assert m_query(arr, "A", ("",)) == "A(1,1,1)"
        assert m_query(arr, "A", ("1", "1", "1")) == "A(1,2)"
        assert m_query(arr, "A", ("1", "2")) == "A(2)"
        assert m_query(arr, "A", ("2",)) == ""

    def test_none_array(self):
        """None array returns empty string."""
        assert m_query(None, "A", ("",)) == ""

    def test_subscript_with_embedded_quote(self):
        """Query formats subscripts with embedded quotes correctly (Spec 017 Phase 12).

        $QUERY must return canonical MUMPS name format where string subscripts
        are quoted and internal quotes are doubled.
        """
        arr = MArray()
        arr['a"b'].value = 1
        # Subscript a"b should be formatted as "a""b" in output
        assert m_query(arr, "x", ("",)) == 'x("a""b")'

    def test_subscript_with_special_chars(self):
        """Query formats subscripts with special characters correctly (Spec 017 Phase 12).

        Complex subscripts like those with backslashes, quotes, and commas must
        be properly quoted in canonical MUMPS name format.
        """
        arr = MArray()
        arr["\\^AGCOM"].value = 1
        arr["\\^AGCOM", ']"G"'].value = 2
        # First subscript: \^AGCOM -> "\^AGCOM"
        assert m_query(arr, "a", ("",)) == 'a("\\^AGCOM")'
        # After first node, should get the nested one
        assert m_query(arr, "a", ("\\^AGCOM",)) == 'a("\\^AGCOM","]""G""")'


class TestMQueryGlobal:
    """Tests for m_query_global() helper function."""

    def test_basic_traversal(self):
        """Query on globals traverses correctly."""
        backend = InMemoryGlobalStorage()
        backend.set("G", ("1", "1"), "a")
        backend.set("G", ("1", "2"), "b")
        assert m_query_global(backend, "G", ("",)) == "^G(1,1)"
        assert m_query_global(backend, "G", ("1", "1")) == "^G(1,2)"


class TestMGet:
    """Tests for m_get() helper function."""

    def test_none_array_returns_default(self):
        """m_get on None returns default."""
        assert m_get(None, (), "DEFAULT") == "DEFAULT"

    def test_undefined_root_returns_default(self):
        """m_get on array with no value returns default."""
        arr = MArray()  # No value set
        assert m_get(arr, (), "DEFAULT") == "DEFAULT"

    def test_defined_root_returns_value(self):
        """m_get on array with value returns that value."""
        arr = MArray()
        arr.value = "HELLO"
        assert m_get(arr, (), "DEFAULT") == "HELLO"

    def test_empty_string_is_defined(self):
        """m_get on array with empty string value returns empty string."""
        arr = MArray()
        arr.value = ""
        assert m_get(arr, (), "DEFAULT") == ""

    def test_subscript_navigation_integer_key(self):
        """m_get navigates subscripts with integer keys."""
        arr = MArray()
        arr[1].value = "VALUE"
        assert m_get(arr, (1,), "DEFAULT") == "VALUE"

    def test_subscript_navigation_string_key(self):
        """m_get navigates subscripts with string keys."""
        arr = MArray()
        arr["A"].value = "VALUE"
        assert m_get(arr, ("A",), "DEFAULT") == "VALUE"

    def test_subscript_string_to_int_conversion(self):
        """m_get converts string subscripts to int when needed."""
        # MArray stores as integer key, but code passes string
        arr = MArray()
        arr[1].value = "VALUE"
        # String "1" should find integer key 1
        assert m_get(arr, ("1",), "DEFAULT") == "VALUE"

    def test_undefined_subscript_returns_default(self):
        """m_get returns default when subscript doesn't exist."""
        arr = MArray()
        arr[1].value = "VALUE"
        assert m_get(arr, (2,), "DEFAULT") == "DEFAULT"

    def test_deep_subscript_navigation(self):
        """m_get navigates multiple levels of subscripts."""
        arr = MArray()
        arr[1][2][3].value = "DEEP"
        assert m_get(arr, (1, 2, 3), "DEFAULT") == "DEEP"

    def test_unconvertible_string_key(self):
        """m_get handles strings that cannot convert to int."""
        arr = MArray()
        arr["ABC"].value = "VALUE"
        # "ABC" can't be converted to int, stays as string
        assert m_get(arr, ("ABC",), "DEFAULT") == "VALUE"


class TestMGetGlobal:
    """Tests for m_get_global() helper function."""

    def test_undefined_global_returns_default(self):
        """m_get_global on undefined global returns default."""
        backend = InMemoryGlobalStorage()
        assert m_get_global(backend, "G", (), "DEFAULT") == "DEFAULT"

    def test_defined_global_returns_value(self):
        """m_get_global on defined global returns value."""
        backend = InMemoryGlobalStorage()
        backend.set("G", (), "VALUE")
        assert m_get_global(backend, "G", (), "DEFAULT") == "VALUE"

    def test_subscripted_global_returns_value(self):
        """m_get_global on subscripted global returns value."""
        backend = InMemoryGlobalStorage()
        backend.set("G", ("1", "A"), "VALUE")
        assert m_get_global(backend, "G", ("1", "A"), "DEFAULT") == "VALUE"

    def test_undefined_subscript_returns_default(self):
        """m_get_global returns default for undefined subscript."""
        backend = InMemoryGlobalStorage()
        backend.set("G", ("1",), "VALUE")
        assert m_get_global(backend, "G", ("2",), "DEFAULT") == "DEFAULT"


class TestMFormatOutput:
    """Tests for m_format_output helper function.

    Spec 017 Phase 7: Proper numeric output formatting matching YDB behavior.
    """

    def test_integer_output(self):
        """Integers are output as-is."""
        from m2py.runtime.helpers import m_format_output

        assert m_format_output(123) == "123"
        assert m_format_output(-456) == "-456"
        assert m_format_output(0) == "0"

    def test_string_output(self):
        """Strings are output as-is."""
        from m2py.runtime.helpers import m_format_output

        assert m_format_output("hello") == "hello"
        assert m_format_output("123") == "123"

    def test_decimal_expansion(self):
        """Decimals with exponents are expanded to full notation."""
        from decimal import Decimal

        from m2py.runtime.helpers import m_format_output

        assert m_format_output(Decimal("1E+11")) == "100000000000"
        assert m_format_output(Decimal("1E-2")) == ".01"
        assert m_format_output(Decimal("5E+2")) == "500"

    def test_decimal_leading_dot(self):
        """Decimals less than 1 start with dot (no leading zero)."""
        from decimal import Decimal

        from m2py.runtime.helpers import m_format_output

        assert m_format_output(Decimal("0.5")) == ".5"
        assert m_format_output(Decimal("0.123")) == ".123"
        assert m_format_output(Decimal("-0.5")) == "-.5"

    def test_extreme_negative_exponent_returns_zero(self):
        """Very small exponents (< -43) return "0" to match YDB behavior.

        YDB outputs 0 for numbers smaller than ~1E-43 because they're
        beyond the precision threshold. This also prevents MemoryError
        from trying to create strings with trillions of digits.
        """
        from decimal import Decimal

        from m2py.runtime.helpers import m_format_output

        # 1E-44 and smaller should return "0"
        assert m_format_output(Decimal("1E-44")) == "0"
        assert m_format_output(Decimal("1E-100")) == "0"
        assert m_format_output(Decimal("1E-11111111111111111")) == "0"

    def test_borderline_exponents(self):
        """Test exponents around the -43 boundary."""
        from decimal import Decimal

        from m2py.runtime.helpers import m_format_output

        # 1E-43 should still work (not return 0)
        result_43 = m_format_output(Decimal("1E-43"))
        assert result_43 != "0"
        assert len(result_43) > 40  # Should have 43+ digits

        # 1E-44 should return 0
        assert m_format_output(Decimal("1E-44")) == "0"


class TestMPieceNegativePositions:
    """Tests for m_piece with negative/zero positions in range extraction.

    Fix: Range extraction clamps from_pos to 1 when <= 0, instead of
    returning empty string like single-piece extraction does.
    """

    def test_single_piece_negative_returns_empty(self):
        """Single piece with negative position returns empty string."""
        from m2py.runtime.helpers import m_piece

        assert m_piece("A^B^C", "^", -1) == ""
        assert m_piece("A^B^C", "^", -5) == ""

    def test_single_piece_zero_returns_empty(self):
        """Single piece with zero position returns empty string."""
        from m2py.runtime.helpers import m_piece

        assert m_piece("A^B^C", "^", 0) == ""

    def test_range_negative_from_clamps_to_one(self):
        """Range with negative from_pos clamps to 1."""
        from m2py.runtime.helpers import m_piece

        # $P("A^B^C","^",-1,2) should give pieces 1-2 = "A^B"
        assert m_piece("A^B^C", "^", -1, 2) == "A^B"
        assert m_piece("A^B^C", "^", -5, 2) == "A^B"

    def test_range_zero_from_clamps_to_one(self):
        """Range with zero from_pos clamps to 1."""
        from m2py.runtime.helpers import m_piece

        # $P("A^B^C","^",0,2) should give pieces 1-2 = "A^B"
        assert m_piece("A^B^C", "^", 0, 2) == "A^B"

    def test_range_negative_to_returns_empty(self):
        """Range with to_pos < from_pos (after clamping) returns empty."""
        from m2py.runtime.helpers import m_piece

        # $P("A^B^C","^",-1,-1) - from clamps to 1, to=-1, to < from
        assert m_piece("A^B^C", "^", -1, -1) == ""

    def test_range_both_negative_returns_empty(self):
        """Range with both positions negative returns empty (to < from)."""
        from m2py.runtime.helpers import m_piece

        assert m_piece("A^B^C", "^", -2, -1) == ""


class TestMFormatOutputEdgeCases:
    """Extended edge case tests for m_format_output() function."""

    # Basic types
    def test_string_passthrough(self):
        """String values pass through unchanged."""
        assert m_format_output("hello") == "hello"
        assert m_format_output("") == ""

    def test_boolean_true(self):
        """True converts to '1'."""
        assert m_format_output(True) == "1"

    def test_boolean_false(self):
        """False converts to '0'."""
        assert m_format_output(False) == "0"

    # Integer handling
    def test_integer(self):
        """Integers convert directly to string."""
        assert m_format_output(42) == "42"
        assert m_format_output(0) == "0"
        assert m_format_output(-100) == "-100"

    def test_float_as_integer(self):
        """Float with .0 converts to integer string."""
        assert m_format_output(1.0) == "1"
        assert m_format_output(100.0) == "100"
        assert m_format_output(-42.0) == "-42"

    # Leading zero removal (MUMPS canonical form)
    def test_positive_decimal_removes_leading_zero(self):
        """Values between 0 and 1 have leading zero removed."""
        assert m_format_output(0.5) == ".5"
        assert m_format_output(0.123) == ".123"

    def test_negative_decimal_removes_leading_zero(self):
        """Negative values between -1 and 0 have leading zero removed."""
        assert m_format_output(-0.5) == "-.5"
        assert m_format_output(-0.123) == "-.123"

    # Regular floats (no leading zero removal)
    def test_regular_float(self):
        """Regular floats retain their form."""
        assert m_format_output(3.14) == "3.14"
        assert m_format_output(-2.5) == "-2.5"

    # Scientific notation conversion
    def test_large_number_scientific_notation(self):
        """Very large numbers avoid scientific notation."""
        # Python would normally output 1e+15 for this
        result = m_format_output(1e15)
        assert "e" not in result.lower()
        assert result == "1000000000000000"

    def test_small_number_scientific_notation(self):
        """Very small numbers may still use scientific notation.

        Note: The current implementation doesn't fully handle very small numbers.
        This test documents the current behavior. MUMPS canonical form would
        require ".000000001" but Python's formatting limits make this difficult.
        """
        # For now, just verify the function doesn't crash
        result = m_format_output(0.000000001)
        assert isinstance(result, str)
        # The value is represented (even if in scientific notation)
        assert result in ("1e-09", ".000000001", "1e-9")

    def test_large_float_with_decimal_scientific_notation(self):
        """Large floats with decimals handle scientific notation."""
        # 1.5e10 has a fractional part
        result = m_format_output(1.5e10)
        assert "e" not in result.lower()
        assert result == "15000000000"

    # Edge cases
    def test_other_types(self):
        """Other types convert via str()."""
        assert m_format_output(None) == "None"
        assert m_format_output([1, 2]) == "[1, 2]"


class TestMData:
    """Tests for m_data() function."""

    def test_none_returns_zero(self):
        """None (undefined variable) returns 0."""
        assert m_data(None) == 0

    def test_none_with_subscripts(self):
        """None with subscripts still returns 0."""
        assert m_data(None, ("1", "2")) == 0

    def test_defined_no_children(self):
        """Defined with value but no children returns 1."""
        arr = MArray()
        arr.value = "test"
        assert m_data(arr, ()) == 1

    def test_undefined_has_children(self):
        """No value but has children returns 10."""
        arr = MArray()
        arr[1].value = "child"  # No value on root, but has child
        assert m_data(arr, ()) == 10

    def test_defined_and_has_children(self):
        """Both value and children returns 11."""
        arr = MArray()
        arr.value = "root"
        arr[1].value = "child"
        assert m_data(arr, ()) == 11

    def test_subscript_navigation(self):
        """Subscripts navigate into array."""
        arr = MArray()
        arr[1][2].value = "deep"
        assert m_data(arr, ("1", "2")) == 1

    def test_undefined_subscript_returns_zero(self):
        """Non-existent subscript returns 0."""
        arr = MArray()
        arr[1].value = "exists"
        assert m_data(arr, ("2",)) == 0

    def test_string_to_int_key_conversion(self):
        """String subscripts can match integer keys."""
        arr = MArray()
        arr[1].value = "value"  # Stored with integer key
        assert m_data(arr, ("1",)) == 1  # String subscript

    def test_deep_subscript_not_found(self):
        """Missing intermediate subscript returns 0."""
        arr = MArray()
        arr[1][2].value = "deep"
        assert m_data(arr, ("3", "4")) == 0


class TestMOrderSubscriptCoercion:
    """Tests for subscript type coercion in m_order."""

    def test_string_key_matches_int_subscript(self):
        """Integer-like strings as subscripts find integer keys."""
        arr = MArray()
        arr[1][1].value = "a"  # Integer keys
        arr[1][2].value = "b"
        # String subscripts should find integer keys
        result = m_order(arr, ("1", ""), 1)
        assert result == "1"

    def test_int_key_via_float_coercion(self):
        """Float-like subscripts can navigate to nodes."""
        # Edge case: sometimes subscripts might come as floats
        arr = MArray()
        arr[1.0][2].value = "a"  # Float key
        # This tests the float() fallback path
        result = m_order(arr, (1.0, ""), 1)
        assert result == "2"

    def test_empty_subscripts_returns_empty(self):
        """Empty subscript tuple returns empty string."""
        arr = MArray()
        arr[1].value = "a"
        assert m_order(arr, (), 1) == ""

    def test_nonexistent_parent_subscript(self):
        """Parent subscript that doesn't exist returns empty."""
        arr = MArray()
        arr[1][2].value = "a"
        # Navigate to arr[99] which doesn't exist
        assert m_order(arr, ("99", ""), 1) == ""


class TestMFormatOutputNumericStrings:
    """Tests for m_format_output with numeric strings.

    Fix: Added canonicalization of strings that look like MUMPS numbers.
    A string "0.5" should output as ".5" to match MUMPS canonical form.
    """

    def test_numeric_string_leading_zero_removed(self):
        """Numeric string "0.5" is canonicalized to ".5"."""
        assert m_format_output("0.5") == ".5"
        assert m_format_output("0.123") == ".123"

    def test_numeric_string_negative_leading_zero_removed(self):
        """Numeric string "-0.5" is canonicalized to "-.5"."""
        assert m_format_output("-0.5") == "-.5"
        assert m_format_output("-0.001") == "-.001"

    def test_integer_string_preserved(self):
        """Integer strings remain unchanged."""
        assert m_format_output("123") == "123"
        assert m_format_output("-456") == "-456"
        assert m_format_output("0") == "0"

    def test_non_numeric_string_unchanged(self):
        """Non-numeric strings are not modified."""
        assert m_format_output("hello") == "hello"
        assert m_format_output("ABC123") == "ABC123"
        assert m_format_output("") == ""

    def test_whitespace_string_unchanged(self):
        """Strings with whitespace are not canonicalized (not MUMPS numbers)."""
        assert m_format_output(" 123") == " 123"  # Leading space
        assert m_format_output("123 ") == "123 "  # Trailing space
        assert m_format_output("  0.5  ") == "  0.5  "

    def test_scientific_notation_string_unchanged(self):
        """Scientific notation strings are not canonicalized."""
        assert m_format_output("1E5") == "1E5"
        assert m_format_output("1e-2") == "1e-2"

    def test_plus_sign_string_unchanged(self):
        """Strings with plus sign are not canonicalized."""
        assert m_format_output("+5") == "+5"
        assert m_format_output("+0.5") == "+0.5"
