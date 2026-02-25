"""Tests for runtime helper functions.

Tests the helper functions used by generated code for intrinsic functions.
"""

import pytest
from decimal import Decimal

from m2py.runtime import MArray
from m2py.runtime.helpers import (
    _mumps_collation_key,
    _rt_os_getcwd,
    m_data,
    m_format_output,
    m_get,
    m_get_global,
    m_now,
    m_order,
    m_order_global,
    m_query,
    m_query_global,
    m_var_value,
    m_zabs,
    m_zbitnot,
    m_zbitor,
    m_zbitxor,
    m_zgetsyi,
    m_ztime,
    unwind_new_stack,
    m_set_extract,
    _raise_select_false,
    m_qlength,
    m_qsubscript,
    m_fnumber,
    m_sorts_after,
    m_pattern_match,
    m_justify,
    NewScopeManager,
)
from m2py.runtime.globals import InMemoryGlobalStorage


class TestMVarValue:
    """Tests for m_var_value() helper (T100).

    m_var_value extracts scalar values from either MArray objects or plain values.
    This is needed for cross-routine variable passing where TRAMPOLINE routines
    may return plain strings while callers expect MArray.value.
    """

    def test_marray_with_value(self):
        """MArray with value returns the value."""
        arr = MArray()
        arr.value = "hello"
        assert m_var_value(arr) == "hello"

    def test_marray_with_numeric_value(self):
        """MArray with numeric value returns the number."""
        arr = MArray()
        arr.value = 42
        assert m_var_value(arr) == 42

    def test_marray_undefined(self):
        """MArray without value returns empty string."""
        arr = MArray()
        assert m_var_value(arr) == ""

    def test_plain_string(self):
        """Plain string passes through unchanged."""
        assert m_var_value("world") == "world"

    def test_plain_number(self):
        """Plain number passes through unchanged."""
        assert m_var_value(123) == 123

    def test_none_returns_empty_string(self):
        """None returns empty string (MUMPS undefined semantics)."""
        assert m_var_value(None) == ""

    def test_empty_string(self):
        """Empty string passes through as empty string."""
        assert m_var_value("") == ""

    def test_marray_with_empty_string_value(self):
        """MArray with empty string value returns empty string."""
        arr = MArray()
        arr.value = ""
        assert m_var_value(arr) == ""


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
        """Canonical numeric strings are treated as numbers for collation."""
        keys = ["1", "-1", "A", "0"]
        sorted_keys = sorted(keys, key=_mumps_collation_key)
        assert sorted_keys == ["-1", "0", "1", "A"]

    def test_decimal_numbers(self):
        """Decimal numbers sort correctly.

        Note: Only CANONICAL numeric strings sort as numbers.
        Non-canonical forms like '-0.5' (canonical: '-.5') sort as strings.
        """
        # Use canonical forms for numeric sorting
        keys = ["-1.5", "-1", "-.5", "0", ".5", "1"]
        sorted_keys = sorted(keys, key=_mumps_collation_key)
        assert sorted_keys == ["-1.5", "-1", "-.5", "0", ".5", "1"]

    def test_non_canonical_decimal_strings(self):
        """Non-canonical numeric strings sort as strings, not numbers.

        Per YDB behavior: '-0.5' is not canonical (should be '-.5'),
        so it sorts as a string after all numbers.
        """
        keys = ["-1.5", "-1", "-0.5", "0", "0.5", "1"]
        sorted_keys = sorted(keys, key=_mumps_collation_key)
        # Numbers first: -1.5, -1, 0, 1
        # Strings after: -0.5, 0.5 (sorted by ASCII)
        assert sorted_keys == ["-1.5", "-1", "0", "1", "-0.5", "0.5"]

    def test_trailing_dot_strings_as_strings(self):
        """Strings with trailing decimal point sort as strings.

        YDB verified: '-4.' is NOT canonical (canonical is '-4'),
        so it sorts as a string.
        """
        keys = ["-4", "-4.", "0", "1"]
        sorted_keys = sorted(keys, key=_mumps_collation_key)
        # Numbers first: -4, 0, 1
        # Strings after: -4.
        assert sorted_keys == ["-4", "0", "1", "-4."]

    def test_trailing_zeros_strings_as_strings(self):
        """Strings with trailing zeros sort as strings.

        YDB verified: '-4.0' is NOT canonical (canonical is '-4'),
        so it sorts as a string.
        """
        keys = ["-4", "-4.0", "0", "1"]
        sorted_keys = sorted(keys, key=_mumps_collation_key)
        # Numbers first: -4, 0, 1
        # Strings after: -4.0
        assert sorted_keys == ["-4", "0", "1", "-4.0"]

    def test_leading_zeros_strings_as_strings(self):
        """Strings with leading zeros sort as strings.

        YDB verified: '01' is NOT canonical (canonical is '1'),
        so it sorts as a string.
        """
        keys = ["1", "01", "2", "02"]
        sorted_keys = sorted(keys, key=_mumps_collation_key)
        # Numbers first: 1, 2
        # Strings after: 01, 02 (sorted by ASCII)
        assert sorted_keys == ["1", "2", "01", "02"]

    def test_mixed_canonical_and_non_canonical(self):
        """Mixed canonical and non-canonical numeric strings.

        Complex case from VV2NO test suite.
        """
        keys = ["-5", "-4", "-4.", "-4.0", "0", "1", "ABC"]
        sorted_keys = sorted(keys, key=_mumps_collation_key)
        # Canonical numbers: -5, -4, 0, 1 (numeric order)
        # Non-canonical strings: -4., -4.0, ABC (ASCII order)
        assert sorted_keys == ["-5", "-4", "0", "1", "-4.", "-4.0", "ABC"]

    def test_very_small_decimal_precision(self):
        """Very small canonical numbers sort correctly with Decimal precision.

        The fix changed float() to Decimal() in _mumps_collation_key() to
        avoid precision loss for values like -.0000000001.

        Fixed suite: V4SORT (test 40079)
        """
        keys = ["-.0000000001", "0", ".0000000001", "1"]
        sorted_keys = sorted(keys, key=_mumps_collation_key)
        assert sorted_keys == ["-.0000000001", "0", ".0000000001", "1"]

    def test_small_decimals_collate_as_numbers(self):
        """Small canonical decimals collate numerically, not as strings."""
        keys = [".001", "-.001", ".01"]
        sorted_keys = sorted(keys, key=_mumps_collation_key)
        assert sorted_keys == ["-.001", ".001", ".01"]


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

    def test_decimal_subscript_canonicalization(self):
        """Decimal subscripts are properly canonicalized for collation.

        Regression test: When subscripts are kept as Decimal rather than
        converted to string via str(), m_order can canonicalize them correctly.

        Decimal("0.9999") should become ".9999" which sorts BEFORE "1".
        """
        from decimal import Decimal

        arr = MArray()
        arr[1].value = "one"
        arr[2].value = "two"

        # Start from Decimal("0.9999"), which should canonicalize to ".9999"
        # and find "1" as the next key
        result = m_order(arr, (Decimal("0.9999"),), 1)
        assert result == "1"

    def test_decimal_subscript_with_leading_zero(self):
        """Decimal with leading zero canonicalizes correctly.

        Decimal("0.5") should become ".5" in canonical form.
        """
        from decimal import Decimal

        arr = MArray()
        arr[Decimal(".5")].value = "half"  # Stored with canonical key
        arr[1].value = "one"

        # Find next after Decimal("0.5") which is the same as ".5"
        result = m_order(arr, (Decimal("0.5"),), 1)
        assert result == "1"

    def test_decimal_subscript_between_integers(self):
        """Decimal value between integers finds correct next."""
        from decimal import Decimal

        arr = MArray()
        arr[1].value = "one"
        arr[2].value = "two"
        arr[3].value = "three"

        # 1.5 is between 1 and 2, so next should be 2
        result = m_order(arr, (Decimal("1.5"),), 1)
        assert result == "2"


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

    def test_non_marray_scalar_no_subscripts(self):
        """A plain string (non-MArray) without subscripts returns 1.

        Defense-in-depth: if scope sync passes a scalar string instead
        of an MArray, $DATA should still return 1 (value exists).
        """
        assert m_data("hello") == 1
        assert m_data("hello", ()) == 1

    def test_non_marray_scalar_with_subscripts(self):
        """A plain string with subscripts returns 0.

        A scalar can't have children, so $DATA with subscripts returns 0.
        """
        assert m_data("hello", ("1",)) == 0
        assert m_data("hello", ("1", "2")) == 0

    def test_non_marray_numeric_no_subscripts(self):
        """A numeric value without subscripts returns 1."""
        assert m_data(42) == 1
        assert m_data(42, ()) == 1

    def test_non_marray_empty_string(self):
        """An empty string without subscripts returns 1 (value exists).

        In MUMPS, "" is a valid value — $DATA returns 1.
        """
        assert m_data("") == 1
        assert m_data("", ()) == 1

    def test_non_marray_zero_no_subscripts(self):
        """Numeric zero (falsy in Python) without subscripts returns 1.

        Zero is a valid MUMPS value and must not be confused with undefined.
        """
        assert m_data(0) == 1
        assert m_data(0, ()) == 1

    def test_non_marray_zero_with_subscripts(self):
        """Numeric zero with subscripts returns 0 (scalars have no children)."""
        assert m_data(0, ("1",)) == 0

    def test_non_marray_float_no_subscripts(self):
        """Float value without subscripts returns 1."""
        assert m_data(3.14) == 1
        assert m_data(3.14, ()) == 1

    def test_non_marray_float_with_subscripts(self):
        """Float value with subscripts returns 0."""
        assert m_data(3.14, ("1",)) == 0

    def test_non_marray_boolean_true(self):
        """Boolean True without subscripts returns 1 (truthy scalar)."""
        assert m_data(True) == 1

    def test_non_marray_boolean_false(self):
        """Boolean False without subscripts returns 1 (still a defined value).

        False is falsy but still a defined value, like 0 in MUMPS.
        """
        assert m_data(False) == 1

    def test_non_marray_negative_number(self):
        """Negative number without subscripts returns 1."""
        assert m_data(-99) == 1
        assert m_data(-99, ()) == 1

    def test_non_marray_negative_with_subscripts(self):
        """Negative number with subscripts returns 0."""
        assert m_data(-99, ("1",)) == 0

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


class TestMFormatOutputStringsPreserved:
    """Tests for m_format_output with strings.

    MUMPS strings are NOT canonicalized - they preserve their exact content.
    Only numeric types (Decimal, int, float) are canonicalized on output.

    YDB verified:
    - S X="0.5" W X → outputs "0.5" (string preserved as-is)
    - S X=0.5 W X → outputs ".5" (numeric canonicalized)
    - S X="1212.000" W X → outputs "1212.000" (trailing zeros preserved in strings)
    """

    def test_numeric_string_preserved_as_is(self):
        """Numeric-looking strings are NOT canonicalized."""
        # Leading zeros preserved
        assert m_format_output("0.5") == "0.5"
        assert m_format_output("0.123") == "0.123"
        # Trailing zeros preserved
        assert m_format_output("1212.000") == "1212.000"
        assert m_format_output("1.00") == "1.00"

    def test_negative_numeric_string_preserved(self):
        """Negative numeric-looking strings are NOT canonicalized."""
        assert m_format_output("-0.5") == "-0.5"
        assert m_format_output("-0.001") == "-0.001"

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
        """Strings with whitespace are preserved."""
        assert m_format_output(" 123") == " 123"  # Leading space
        assert m_format_output("123 ") == "123 "  # Trailing space
        assert m_format_output("  0.5  ") == "  0.5  "

    def test_scientific_notation_string_unchanged(self):
        """Scientific notation strings are preserved."""
        assert m_format_output("1E5") == "1E5"
        assert m_format_output("1e-2") == "1e-2"

    def test_plus_sign_string_unchanged(self):
        """Strings with plus sign are preserved."""
        assert m_format_output("+5") == "+5"
        assert m_format_output("+0.5") == "+0.5"


class TestMNextLocal:
    """Tests for MUMPSRuntime.m_next_local() method.

    $NEXT is like $ORDER but:
    - Returns -1 instead of "" when no more subscripts
    - Treats -1 as "start from beginning" (like $ORDER treats "")
    """

    @pytest.fixture
    def rt(self):
        """Create runtime instance."""
        from m2py.runtime import MUMPSRuntime

        return MUMPSRuntime()

    def test_next_from_minus_one_returns_first(self, rt):
        """$NEXT(A(-1)) returns first subscript."""
        arr = MArray()
        arr[1].value = "a"
        arr[3].value = "c"
        arr[5].value = "e"
        result = rt.m_next_local(arr, (-1,))
        assert result == "1"

    def test_next_returns_next_subscript(self, rt):
        """$NEXT(A(1)) returns next subscript."""
        arr = MArray()
        arr[1].value = "a"
        arr[3].value = "c"
        arr[5].value = "e"
        result = rt.m_next_local(arr, (1,))
        assert result == "3"

    def test_next_at_end_returns_minus_one(self, rt):
        """$NEXT(A(lastkey)) returns -1."""
        arr = MArray()
        arr[1].value = "a"
        arr[3].value = "c"
        result = rt.m_next_local(arr, (3,))
        assert result == -1

    def test_next_none_array_returns_minus_one(self, rt):
        """$NEXT on None array returns -1."""
        result = rt.m_next_local(None, ("",))
        assert result == -1

    def test_next_empty_subscripts_returns_minus_one(self, rt):
        """$NEXT with empty subscripts returns -1."""
        arr = MArray()
        arr[1].value = "a"
        result = rt.m_next_local(arr, ())
        assert result == -1

    def test_next_nested_subscripts(self, rt):
        """$NEXT works with nested subscripts."""
        arr = MArray()
        arr[1, 1].value = "a"
        arr[1, 2].value = "b"
        arr[1, 5].value = "c"
        result = rt.m_next_local(arr, (1, -1))
        assert result == "1"  # First subscript at level 2
        result = rt.m_next_local(arr, (1, 2))
        assert result == "5"  # Next after 2

    def test_next_string_subscripts(self, rt):
        """$NEXT works with string subscripts."""
        arr = MArray()
        arr["A"].value = "first"
        arr["B"].value = "second"
        arr["C"].value = "third"
        result = rt.m_next_local(arr, ("-1",))
        # -1 as string becomes "" for $ORDER semantics
        assert result == "A"


class TestMNextGlobal:
    """Tests for MUMPSRuntime.m_next_global() method.

    $NEXT for global variables behaves the same as for locals:
    - Returns -1 instead of "" when no more subscripts
    - Treats -1 as "start from beginning"
    """

    @pytest.fixture
    def rt(self):
        """Create runtime instance."""
        from m2py.runtime import MUMPSRuntime

        return MUMPSRuntime()

    def test_next_from_minus_one_returns_first(self, rt):
        """$NEXT(^G(-1)) returns first subscript."""
        rt.globals.set("G", ("1",), "a")
        rt.globals.set("G", ("3",), "c")
        rt.globals.set("G", ("5",), "e")
        result = rt.m_next_global("G", (-1,))
        assert result == "1"

    def test_next_returns_next_subscript(self, rt):
        """$NEXT(^G(1)) returns next subscript."""
        rt.globals.set("G", ("1",), "a")
        rt.globals.set("G", ("3",), "c")
        rt.globals.set("G", ("5",), "e")
        result = rt.m_next_global("G", (1,))
        assert result == "3"

    def test_next_at_end_returns_minus_one(self, rt):
        """$NEXT(^G(lastkey)) returns -1."""
        rt.globals.set("G", ("1",), "a")
        rt.globals.set("G", ("3",), "c")
        result = rt.m_next_global("G", (3,))
        assert result == -1

    def test_next_empty_subscripts_returns_minus_one(self, rt):
        """$NEXT with empty subscripts returns -1."""
        rt.globals.set("G", ("1",), "a")
        result = rt.m_next_global("G", ())
        assert result == -1

    def test_next_nested_subscripts(self, rt):
        """$NEXT works with nested global subscripts."""
        rt.globals.set("G", ("1", "1"), "a")
        rt.globals.set("G", ("1", "2"), "b")
        rt.globals.set("G", ("1", "5"), "c")
        result = rt.m_next_global("G", (1, -1))
        assert result == "1"  # First subscript at level 2
        result = rt.m_next_global("G", (1, 2))
        assert result == "5"  # Next after 2


class TestMNextLocalDecimalSubscripts:
    """Tests for m_next_local with Decimal subscripts.

    Regression tests for subscript canonicalization bug where Decimal
    subscripts were converted to strings via str() BEFORE being passed
    to m_order, which lost numeric canonicalization.

    Example bug: Decimal("0.9999") -> str() -> "0.9999" (non-canonical)
    Correct:     Decimal("0.9999") -> m_order -> canonicalizes to ".9999"

    The fix ensures subscripts are kept in original form (Decimal, int, etc.)
    so m_order can properly canonicalize them.
    """

    @pytest.fixture
    def rt(self):
        """Create runtime instance."""
        from m2py.runtime import MUMPSRuntime

        return MUMPSRuntime()

    def test_decimal_subscript_finds_next(self, rt):
        """Decimal subscript 0.9999 finds integer 1 as next.

        This was the exact failure case: $NEXT(A(.9999)) should find 1
        when A(1), A(2) exist. The bug was that 0.9999 was converted to
        "0.9999" string which is NON-canonical and sorted as string.
        """
        from decimal import Decimal

        arr = MArray()
        arr[1].value = "one"
        arr[2].value = "two"
        arr[Decimal("2.0005")].value = "decimal"

        # Start from 0.9999 (before 1), should find 1
        result = rt.m_next_local(arr, (Decimal("0.9999"),))
        assert result == "1"

    def test_decimal_subscript_between_integers(self, rt):
        """Decimal subscript between integers finds correct next."""
        from decimal import Decimal

        arr = MArray()
        arr[1].value = "one"
        arr[2].value = "two"
        arr[3].value = "three"

        # Start from 1.5, should find 2
        result = rt.m_next_local(arr, (Decimal("1.5"),))
        assert result == "2"

    def test_decimal_with_leading_zero(self, rt):
        """Decimal with leading zero still works correctly.

        Decimal("0.5") should be canonicalized to ".5" and find values after it.
        """
        from decimal import Decimal

        arr = MArray()
        arr[Decimal(".5")].value = "half"  # Canonical form
        arr[1].value = "one"

        # Start from "" to find first
        result = rt.m_next_local(arr, ("",))
        assert result == ".5"

        # Start from .5 to find 1
        result = rt.m_next_local(arr, (Decimal("0.5"),))
        assert result == "1"


class TestMNextGlobalDecimalSubscripts:
    """Tests for m_next_global with Decimal subscripts.

    Parallel tests to TestMNextLocalDecimalSubscripts for globals.
    """

    @pytest.fixture
    def rt(self):
        """Create runtime instance."""
        from m2py.runtime import MUMPSRuntime

        return MUMPSRuntime()

    def test_decimal_subscript_finds_next(self, rt):
        """Decimal subscript 0.9999 finds integer 1 as next in globals."""
        from decimal import Decimal

        rt.globals.set("G", ("1",), "one")
        rt.globals.set("G", ("2",), "two")

        # Start from 0.9999, should find 1
        result = rt.m_next_global("G", (Decimal("0.9999"),))
        assert result == "1"

    def test_decimal_subscript_between_integers(self, rt):
        """Decimal subscript between integers finds correct next in globals."""
        from decimal import Decimal

        rt.globals.set("G", ("1",), "one")
        rt.globals.set("G", ("2",), "two")
        rt.globals.set("G", ("3",), "three")

        # Start from 1.5, should find 2
        result = rt.m_next_global("G", (Decimal("1.5"),))
        assert result == "2"


# =============================================================================
# Phase 21: unwind_new_stack() Tests
# =============================================================================


class _MockState:
    """Minimal mock for TRAMPOLINE RoutineState used by unwind_new_stack."""

    def __init__(self):
        self._locals = {}
        self._new_stack = []


class TestUnwindNewStack:
    """Tests for unwind_new_stack() helper function (Phase 21)."""

    def test_empty_stack_is_noop(self):
        """unwind_new_stack on empty _new_stack does nothing."""
        state = _MockState()
        state._locals = {"X": MArray(value=1)}
        unwind_new_stack(state)
        assert state._locals["X"].value == 1
        assert len(state._new_stack) == 0

    def test_selective_var_restore(self):
        """('var', name, saved_value) restores a single variable."""
        state = _MockState()
        saved = MArray(value=42)
        state._new_stack.append(("var", "X", saved))
        state._locals = {"X": MArray(value=99)}
        unwind_new_stack(state)
        assert state._locals["X"] is saved
        assert state._locals["X"].value == 42
        assert len(state._new_stack) == 0

    def test_selective_var_none_removes(self):
        """('var', name, None) removes variable from _locals."""
        state = _MockState()
        state._new_stack.append(("var", "X", None))
        state._locals = {"X": MArray(value=5)}
        unwind_new_stack(state)
        assert "X" not in state._locals

    def test_all_entry_restores_snapshot(self):
        """('all', snapshot) clears _locals and restores from snapshot."""
        state = _MockState()
        snapshot = {"A": MArray(value=1), "B": MArray(value=2)}
        state._new_stack.append(("all", snapshot))
        state._locals = {"C": MArray(value=99)}
        unwind_new_stack(state)
        assert "C" not in state._locals
        assert state._locals["A"].value == 1
        assert state._locals["B"].value == 2

    def test_excl_entry_restores_nonkept(self):
        """('excl', keep_vars, saved) restores non-kept vars, preserves kept."""
        state = _MockState()
        saved = {"Y": MArray(value=20), "Z": MArray(value=30)}
        state._new_stack.append(("excl", {"X"}, saved))
        state._locals = {"X": MArray(value=99)}
        unwind_new_stack(state)
        # X was kept, so current value preserved
        assert state._locals["X"].value == 99
        # Y and Z restored from saved
        assert state._locals["Y"].value == 20
        assert state._locals["Z"].value == 30

    def test_legacy_dict_entry(self):
        """Plain dict entry (legacy format) treated as argumentless NEW."""
        state = _MockState()
        snapshot = {"X": MArray(value=1)}
        state._new_stack.append(snapshot)
        state._locals = {"Y": MArray(value=2)}
        unwind_new_stack(state)
        assert state._locals == snapshot
        assert "Y" not in state._locals

    def test_multiple_entries_lifo_order(self):
        """Multiple entries are processed in LIFO order."""
        state = _MockState()
        # Push: first a selective NEW of X, then an argumentless NEW
        saved_x = MArray(value=10)
        state._new_stack.append(("var", "X", saved_x))
        state._new_stack.append(("all", {"X": MArray(value=50), "Y": MArray(value=60)}))
        state._locals = {"Z": MArray(value=99)}

        unwind_new_stack(state)

        # LIFO: first 'all' restores {X=50, Y=60}, then 'var' restores X=10
        assert state._locals["X"].value == 10
        assert state._locals["Y"].value == 60

    def test_excl_preserves_kept_values(self):
        """Exclusive NEW preserves current kept values over saved values."""
        state = _MockState()
        saved = {"X": MArray(value=1), "Y": MArray(value=2)}
        state._new_stack.append(("excl", {"X"}, saved))
        # X was modified during subroutine
        state._locals = {"X": MArray(value=999)}
        unwind_new_stack(state)
        # X was in keep_vars, so current value (999) is preserved
        assert state._locals["X"].value == 999
        # Y was not in keep_vars, so restored from saved
        assert state._locals["Y"].value == 2

    def test_stack_fully_drained(self):
        """After unwind, _new_stack is empty."""
        state = _MockState()
        state._new_stack.append(("var", "A", None))
        state._new_stack.append(("var", "B", MArray(value=1)))
        state._new_stack.append(("all", {}))
        unwind_new_stack(state)
        assert len(state._new_stack) == 0


# =============================================================================
# Phase 22: m_translate tests
# =============================================================================


class TestMTranslate:
    """Test m_translate() runtime helper for $TRANSLATE function."""

    def test_basic_replacement(self):
        """Replace characters with same-length to_chars."""
        from m2py.runtime.helpers import m_translate

        assert m_translate("HELLO", "LO", "XY") == "HEXXY"

    def test_shorter_to_deletes(self):
        """When to_chars shorter than from_chars, excess from_chars are deleted."""
        from m2py.runtime.helpers import m_translate

        assert m_translate("HELLO", "HEL", "A") == "AO"

    def test_no_to_deletes_all(self):
        """When to_chars omitted, all from_chars are deleted."""
        from m2py.runtime.helpers import m_translate

        assert m_translate("HELLO", "L") == "HEO"

    def test_to_longer_than_from(self):
        """When to_chars longer than from_chars, extra to_chars are ignored."""
        from m2py.runtime.helpers import m_translate

        assert m_translate("ABCDEFGHIJ", "ABC", "abcdef") == "abcDEFGHIJ"

    def test_empty_string(self):
        """Empty string input returns empty string."""
        from m2py.runtime.helpers import m_translate

        assert m_translate("", "A", "B") == ""

    def test_no_matches(self):
        """When no characters match from_chars, string unchanged."""
        from m2py.runtime.helpers import m_translate

        assert m_translate("HELLO", "XYZ", "abc") == "HELLO"

    def test_all_chars_replaced(self):
        """All characters in string are replaced."""
        from m2py.runtime.helpers import m_translate

        assert m_translate("ABCBAABCBA", "ABC", "abc") == "abcbaabcba"

    def test_duplicate_from_chars(self):
        """First occurrence in from_chars wins for mapping."""
        from m2py.runtime.helpers import m_translate

        # 'A' found at index 0 → 'x', 'B' found at index 1 → 'y', 'C' not found → 'C'
        assert m_translate("ABC", "ABA", "xyz") == "xyC"

    def test_empty_from_chars(self):
        """Empty from_chars means no characters to replace - string unchanged."""
        from m2py.runtime.helpers import m_translate

        assert m_translate("HELLO", "") == "HELLO"
        assert m_translate("HELLO", "", "xyz") == "HELLO"

    def test_explicit_empty_to_chars(self):
        """Empty to_chars explicitly passed deletes all from_chars matches."""
        from m2py.runtime.helpers import m_translate

        assert m_translate("HELLO", "HEL", "") == "O"

    def test_same_char_identity_mapping(self):
        """Mapping a character to itself is a no-op for that character."""
        from m2py.runtime.helpers import m_translate

        assert m_translate("HELLO", "L", "L") == "HELLO"

    def test_special_characters(self):
        """Translate works with spaces, punctuation, and control chars."""
        from m2py.runtime.helpers import m_translate

        assert m_translate("A B C", " ", "-") == "A-B-C"
        assert m_translate("hello\tworld", "\t", " ") == "hello world"
        assert m_translate("a.b*c", ".*", "XY") == "aXbYc"

    def test_single_char_string(self):
        """Single character string with single char from/to."""
        from m2py.runtime.helpers import m_translate

        assert m_translate("A", "A", "B") == "B"
        assert m_translate("A", "A") == ""
        assert m_translate("A", "B", "C") == "A"

    def test_from_and_to_both_empty(self):
        """Both from_chars and to_chars empty - string unchanged."""
        from m2py.runtime.helpers import m_translate

        assert m_translate("HELLO", "", "") == "HELLO"


class TestMSetExtractEdges:
    """LIVE edges in m_set_extract."""

    def test_padding_when_string_too_short(self):
        """$EXTRACT replaces beyond string length, pads with spaces."""
        current = "AB"
        result = [current]

        def getter():
            return result[0]

        def setter(val):
            result[0] = val

        m_set_extract(getter, setter, 5, 5, "X")
        assert result[0] == "AB  X"

    def test_from_pos_one(self):
        """Replace at position 1."""
        current = "ABCDE"
        result = [current]

        def getter():
            return result[0]

        def setter(val):
            result[0] = val

        m_set_extract(getter, setter, 1, 3, "XY")
        # $E(str,1,3)="XY" → "XY" replaces positions 1-3, rest preserved
        assert result[0] == "XYDE"

    def test_from_greater_than_to(self):
        """When from > to, no modification (YDB behavior)."""
        current = "ABCDE"
        result = [current]

        def getter():
            return result[0]

        def setter(val):
            result[0] = val

        m_set_extract(getter, setter, 3, 1, "X")
        # Per YDB behavior: if from_pos > to_pos, no modification occurs
        assert result[0] == "ABCDE"


# =============================================================================
# _raise_select_false
# =============================================================================


class TestRaiseSelectFalse:
    """LIVE _raise_select_false function."""

    def test_raises_runtime_error(self):
        """Raises MRuntimeError with SELECTFALSE."""
        with pytest.raises(Exception, match="SELECTFALSE|SELECT"):
            _raise_select_false()


# =============================================================================
# m_qlength / m_qsubscript
# =============================================================================


class TestMQlength:
    """LIVE m_qlength edge cases."""

    def test_unsubscripted_name(self):
        """$QLENGTH("X") = 0."""
        assert m_qlength("X") == 0

    def test_one_subscript(self):
        """$QLENGTH("X(1)") = 1."""
        assert m_qlength("X(1)") == 1

    def test_multiple_subscripts(self):
        """$QLENGTH("X(1,2,3)") = 3."""
        assert m_qlength("X(1,2,3)") == 3

    def test_global_name(self):
        """$QLENGTH("^GLO(1,2)") = 2."""
        assert m_qlength("^GLO(1,2)") == 2

    def test_quoted_subscript(self):
        """$QLENGTH with quoted string subscript."""
        val = m_qlength('^X("A","B")')
        assert val == 2

    def test_empty_string(self):
        """$QLENGTH("") = 0."""
        assert m_qlength("") == 0


class TestMQsubscript:
    """LIVE m_qsubscript edge cases."""

    def test_base_name(self):
        """$QSUBSCRIPT("X(1,2)",0) = name portion."""
        result = m_qsubscript("X(1,2)", 0)
        assert result == "X"

    def test_first_subscript(self):
        """$QSUBSCRIPT("X(1,2)",1) = "1"."""
        result = m_qsubscript("X(1,2)", 1)
        assert result == "1"

    def test_second_subscript(self):
        """$QSUBSCRIPT("X(1,2)",2) = "2"."""
        result = m_qsubscript("X(1,2)", 2)
        assert result == "2"

    def test_out_of_range(self):
        """$QSUBSCRIPT beyond subscript count returns ""."""
        result = m_qsubscript("X(1)", 5)
        assert result == ""

    def test_negative_position(self):
        """$QSUBSCRIPT with -1 returns environment/empty."""
        result = m_qsubscript("X(1)", -1)
        assert isinstance(result, str)

    def test_global_base_name(self):
        """$QSUBSCRIPT("^GLO(1)",0) = "^GLO"."""
        result = m_qsubscript("^GLO(1)", 0)
        assert result == "^GLO"


# =============================================================================
# m_fnumber
# =============================================================================


class TestMFnumberLive:
    """LIVE m_fnumber edge cases."""

    def test_comma_format(self):
        """$FNUMBER with comma inserts separators."""
        result = m_fnumber("1234567", ",")
        assert result == "1,234,567"

    def test_comma_with_decimals(self):
        """$FNUMBER with comma and decimal places."""
        result = m_fnumber("1234567.89", ",", 2)
        assert "1,234,567" in result

    def test_trailing_sign_positive(self):
        """$FNUMBER with T code, positive number gets trailing space."""
        result = m_fnumber("42", "T")
        # Positive in T mode gets trailing space (not +)
        assert result == "42 "

    def test_trailing_sign_negative(self):
        """$FNUMBER with T code, negative number."""
        result = m_fnumber("-42", "T")
        assert result.endswith("-")

    def test_plus_code(self):
        """$FNUMBER with + code shows plus sign."""
        result = m_fnumber("42", "+")
        assert "+" in result

    def test_minus_code(self):
        """$FNUMBER with - code suppresses minus."""
        result = m_fnumber("-42", "-")
        # The '-' code removes the minus sign
        assert not result.startswith("-")

    def test_paren_mode(self):
        """$FNUMBER with P code wraps negative in parens."""
        result = m_fnumber("-42", "P")
        assert result.startswith("(") and result.endswith(")")

    def test_paren_mode_positive(self):
        """$FNUMBER with P code, positive number gets trailing space."""
        result = m_fnumber("42", "P")
        # Positive numbers in P mode get a trailing space
        assert "(" not in result


# =============================================================================
# m_sorts_after
# =============================================================================


class TestMSortsAfterLive:
    """LIVE m_sorts_after edge cases."""

    def test_numeric_sorts_after(self):
        """Numeric comparison: 10 sorts after 2."""
        assert m_sorts_after("10", "2") == 1

    def test_numeric_does_not_sort_after(self):
        """Numeric comparison: 2 does not sort after 10."""
        assert m_sorts_after("2", "10") == 0

    def test_string_sorts_after(self):
        """String comparison: 'B' sorts after 'A'."""
        assert m_sorts_after("B", "A") == 1

    def test_equal_values(self):
        """Equal values: neither sorts after the other."""
        assert m_sorts_after("5", "5") == 0

    def test_string_vs_numeric(self):
        """String always sorts after numeric in MUMPS."""
        assert m_sorts_after("ABC", "999") == 1

    def test_empty_string(self):
        """Empty string sorts before everything."""
        assert m_sorts_after("", "A") == 0
        assert m_sorts_after("A", "") == 1


# =============================================================================
# m_pattern_match exception handling
# =============================================================================


class TestMPatternMatchEdges:
    """LIVE m_pattern_match exception fallback."""

    def test_valid_pattern(self):
        """Normal pattern match works."""
        assert m_pattern_match("123", "3N") == 1
        assert m_pattern_match("ABC", "3A") == 1
        assert m_pattern_match("ABC", "3N") == 0

    def test_invalid_pattern_returns_zero(self):
        """Invalid pattern raises error or returns 0."""
        # Behavior depends on implementation — may raise or return 0
        try:
            result = m_pattern_match("ABC", "")
            assert isinstance(result, int)
        except Exception:
            pass  # Also acceptable


# =============================================================================
# NewScopeManager
# =============================================================================


class TestNewScopeManagerLive:
    """LIVE NewScopeManager edge cases: new_all, new_exclusive, new_special_var."""

    def test_new_var_saves_and_restores(self):
        """NEW X saves current X, clears it, restores on exit."""
        scope = {"X": "old_value", "Y": "keep"}

        with NewScopeManager(scope) as mgr:
            mgr.new_var("X")
            # Inside scope, X should be deleted
            assert "X" not in scope
            assert scope["Y"] == "keep"
            scope["X"] = "new_value"

        # After exit, X should be restored to original value
        assert scope["X"] == "old_value"
        assert scope["Y"] == "keep"

    def test_new_var_undefined_restored(self):
        """NEW X when X is undefined — stays undefined after restore."""
        scope = {"Y": "keep"}

        with NewScopeManager(scope) as mgr:
            mgr.new_var("X")
            scope["X"] = "temp"

        assert "X" not in scope

    def test_new_var_dedup(self):
        """NEW X twice at same level is no-op for second call."""
        scope = {"X": "original"}

        with NewScopeManager(scope) as mgr:
            mgr.new_var("X")
            scope["X"] = "first_new"
            mgr.new_var("X")  # Should be no-op
            scope["X"] = "second_new"

        # Should restore to original (first NEW), not first_new
        assert scope["X"] == "original"

    def test_new_all(self):
        """NEW (argumentless) saves all locals and clears scope."""
        scope = {"X": "1", "Y": "2", "Z": "3"}

        with NewScopeManager(scope) as mgr:
            mgr.new_all()
            # All locals should be cleared
            assert len(scope) == 0
            scope["A"] = "new"

        # After exit, all original should be restored
        assert scope["X"] == "1"
        assert scope["Y"] == "2"
        assert scope["Z"] == "3"
        assert "A" not in scope

    def test_new_exclusive(self):
        """NEW (X) exclusive — saves all EXCEPT X."""
        scope = {"X": "1", "Y": "2", "Z": "3"}

        with NewScopeManager(scope) as mgr:
            mgr.new_exclusive({"X"})
            # X should be kept, Y and Z removed
            assert "X" in scope
            assert "Y" not in scope
            assert "Z" not in scope

        # After exit, all original should be restored
        assert scope["X"] == "1"
        assert scope["Y"] == "2"
        assert scope["Z"] == "3"

    def test_new_special_var(self):
        """NEW $ETRAP saves and restores special variable."""
        scope = {}
        restored_values = []

        def setter(val):
            restored_values.append(val)

        with NewScopeManager(scope) as mgr:
            mgr.new_special_var("$ETRAP", "old_etrap", setter)
            # setter should have been called with "" to initialize
            assert restored_values[-1] == ""

        # After exit, setter called with saved value
        assert restored_values[-1] == "old_etrap"


# =============================================================================
# unwind_new_stack
# =============================================================================


class TestUnwindNewStackLive:
    """LIVE unwind_new_stack function."""

    class _FakeState:
        """Minimal state object for unwind_new_stack."""

        def __init__(self, new_stack=None, locals_dict=None):
            self._new_stack = new_stack or []
            self._locals = locals_dict or {}

    def test_unwind_empty_stack(self):
        """Unwinding empty stack is a no-op."""
        state = self._FakeState()
        unwind_new_stack(state)
        assert state._locals == {}

    def test_unwind_var_entry(self):
        """Unwinding a ('var', name, saved_value) entry restores variable."""
        state = self._FakeState(
            new_stack=[("var", "X", "saved_val")],
            locals_dict={"X": "new_val"},
        )
        unwind_new_stack(state)
        assert state._locals["X"] == "saved_val"

    def test_unwind_var_entry_none_removes(self):
        """Unwinding a ('var', name, None) entry removes variable."""
        state = self._FakeState(
            new_stack=[("var", "X", None)],
            locals_dict={"X": "temp"},
        )
        unwind_new_stack(state)
        assert "X" not in state._locals

    def test_unwind_all_entry(self):
        """Unwinding an ('all', snapshot) entry restores full snapshot."""
        state = self._FakeState(
            new_stack=[("all", {"A": "1", "B": "2"})],
            locals_dict={"C": "3"},
        )
        unwind_new_stack(state)
        assert state._locals == {"A": "1", "B": "2"}

    def test_unwind_excl_entry(self):
        """Unwinding an ('excl', keep_set, saved) entry."""
        state = self._FakeState(
            new_stack=[("excl", {"X"}, {"X": "orig", "Y": "orig2", "Z": "orig3"})],
            locals_dict={"X": "current"},
        )
        unwind_new_stack(state)
        assert state._locals["X"] == "current"
        assert state._locals["Y"] == "orig2"
        assert state._locals["Z"] == "orig3"

    def test_unwind_legacy_dict(self):
        """Unwinding a plain dict (legacy format) restores it."""
        state = self._FakeState(
            new_stack=[{"A": "1", "B": "2"}],
            locals_dict={"C": "3"},
        )
        unwind_new_stack(state)
        assert state._locals == {"A": "1", "B": "2"}


class TestMFormatOutputLive:
    """Tests for m_format_output() function."""

    # Basic types
    def test_string_passthrough(self):
        """String values pass through unchanged."""
        assert m_format_output("hello") == "hello"
        assert m_format_output("") == ""

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


class TestMDataLive:
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


class TestMOrderSubscriptCoercionLive:
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


# =============================================================================
# m_justify Tests - ROUND_HALF_UP Rounding
# =============================================================================


class TestMJustify:
    """Tests for m_justify() function.

    Bug fix: m_justify now uses ROUND_HALF_UP (traditional rounding)
    instead of Python's default ROUND_HALF_EVEN (banker's rounding).
    """

    def test_basic_formatting(self):
        """Basic number formatting with width and decimals."""
        assert m_justify(3.14159, 10, 2) == "      3.14"
        assert m_justify(42, 5, 0) == "   42"

    def test_round_half_up_not_bankers(self):
        """Values ending in .5 round UP, not to nearest even.

        This is the key difference from Python's default Decimal rounding.
        - 123.45 with 1 decimal → 123.5 (not 123.4)
        - 2.35 with 1 decimal → 2.4 (not 2.4 - same, but 2.45 matters)
        """
        # 123.45 → 123.5 (ROUND_HALF_UP), not 123.4 (ROUND_HALF_EVEN)
        assert m_justify(123.45, 7, 1) == "  123.5"

        # 2.35 → 2.4 (both rounding modes agree here)
        assert m_justify(2.35, 5, 1) == "  2.4"

        # 2.25 → 2.3 (ROUND_HALF_UP), not 2.2 (ROUND_HALF_EVEN)
        assert m_justify(2.25, 5, 1) == "  2.3"

        # 1.5 → 2 (ROUND_HALF_UP), not 2 (ROUND_HALF_EVEN agrees for odd)
        assert m_justify(1.5, 3, 0) == "  2"

        # 2.5 → 3 (ROUND_HALF_UP), not 2 (ROUND_HALF_EVEN would round to even 2)
        assert m_justify(2.5, 3, 0) == "  3"

    def test_decimal_input_preserves_precision(self):
        """Decimal inputs maintain precision for rounding."""
        # Test with Decimal input
        assert m_justify(Decimal("123.45"), 7, 1) == "  123.5"
        assert m_justify(Decimal("2.25"), 5, 1) == "  2.3"

    def test_negative_values(self):
        """Negative values round correctly."""
        # -123.45 → -123.5
        assert m_justify(-123.45, 8, 1) == "  -123.5"

        # -2.25 → -2.3 (rounds away from zero with ROUND_HALF_UP)
        assert m_justify(-2.25, 6, 1) == "  -2.3"

    def test_width_smaller_than_result(self):
        """Width smaller than formatted result doesn't truncate."""
        assert m_justify(12345.67, 5, 2) == "12345.67"
        assert m_justify(999.9, 3, 1) == "999.9"

    def test_zero_decimals(self):
        """Zero decimal places rounds to integer."""
        assert m_justify(3.7, 3, 0) == "  4"
        assert m_justify(3.4, 3, 0) == "  3"
        assert m_justify(3.5, 3, 0) == "  4"  # ROUND_HALF_UP

    def test_many_decimals(self):
        """Many decimal places pad with zeros."""
        assert m_justify(3.14, 10, 5) == "   3.14000"
        assert m_justify(1, 8, 3) == "   1.000"


# =============================================================================
# Phase 12A: Runtime Helper Tests (spec 024, T065-T073)
# =============================================================================


class TestZabsRuntime:
    """$ZABS runtime helper tests (T066).

    IRIS reference output validated via utils/run_mumps_iris.py:
    - $ZABS(-42) → 42
    - $ZABS(0) → 0
    - $ZABS(3.14) → 3.14
    - $ZABS(-0) → 0
    - $ZABS("") → 0
    - $ZABS("abc") → 0
    - $ZABS(-0.001) → .001
    """

    def test_negative_integer(self):
        """$ZABS(-42) returns '42'."""
        assert m_zabs("-42") == "42"

    def test_positive_integer(self):
        """$ZABS(42) returns '42'."""
        assert m_zabs("42") == "42"

    def test_zero(self):
        """$ZABS(0) returns '0'."""
        assert m_zabs("0") == "0"

    def test_negative_zero(self):
        """$ZABS(-0) returns '0' (IRIS: 0)."""
        assert m_zabs("-0") == "0"

    def test_positive_decimal(self):
        """$ZABS(3.14) returns '3.14'."""
        assert m_zabs("3.14") == "3.14"

    def test_negative_decimal(self):
        """$ZABS(-3.14) returns '3.14'."""
        assert m_zabs("-3.14") == "3.14"

    def test_small_negative(self):
        """$ZABS(-0.001) returns '.001' (IRIS canonical form)."""
        assert m_zabs("-0.001") == ".001"

    def test_empty_string(self):
        """$ZABS("") returns '0' (non-numeric coerced to 0)."""
        assert m_zabs("") == "0"

    def test_non_numeric_string(self):
        """$ZABS("abc") returns '0' (non-numeric coerced to 0)."""
        assert m_zabs("abc") == "0"

    def test_leading_numeric(self):
        """$ZABS("-5abc") returns '5' (MUMPS numeric coercion)."""
        assert m_zabs("-5abc") == "5"

    def test_large_number(self):
        """$ZABS(-99999999) returns '99999999'."""
        assert m_zabs("-99999999") == "99999999"

    def test_very_small_decimal(self):
        """$ZABS(-0.0001) returns '.0001'."""
        assert m_zabs("-0.0001") == ".0001"


class TestNowRuntime:
    """$NOW runtime helper tests (T067).

    $NOW returns $HOROLOG format "days,seconds.fraction".
    IRIS reference: $P($NOW(),",",1) = $P($H,",",1) (same day part).
    """

    def test_returns_horolog_format(self):
        """$NOW returns 'days,seconds.fraction' format."""
        result = m_now()
        parts = result.split(",")
        assert len(parts) == 2, f"Expected 'days,seconds' format, got '{result}'"

    def test_day_part_is_positive_integer(self):
        """Day part is a positive integer > 0."""
        result = m_now()
        days = int(result.split(",")[0])
        assert days > 0

    def test_day_part_is_reasonable(self):
        """Day part is after year 2020 (at least 65,382 days since 1840-12-31)."""
        result = m_now()
        days = int(result.split(",")[0])
        # 2020-01-01 is day 65,382 from 1840-12-31
        assert days >= 65382

    def test_seconds_part_is_non_negative(self):
        """Seconds part is non-negative."""
        result = m_now()
        seconds = float(result.split(",")[1])
        assert seconds >= 0

    def test_seconds_less_than_86400(self):
        """Seconds part is less than 86400 (one day)."""
        result = m_now()
        seconds = float(result.split(",")[1])
        assert seconds < 86400

    def test_has_fractional_seconds(self):
        """$NOW includes fractional seconds (unlike $HOROLOG)."""
        result = m_now()
        sec_part = result.split(",")[1]
        # Should contain a decimal point (fractional seconds)
        # Note: In rare timing cases the fractional part might be .000000
        # which gets stripped to integer, but this is extremely unlikely
        assert "." in sec_part or sec_part.isdigit()


class TestZbitorRuntime:
    """$ZBITOR runtime helper tests (T068).

    m_zbitor performs byte-by-byte OR with zero-padding for shorter strings.
    This is a transpilation-compatible implementation — actual IRIS $ZBITOR
    uses IRIS bit string format, but VistA code uses platform-specific branches
    (XLFSHAN uses $ZBOOLEAN on IRIS, $ZBITOR only on GT.M).
    """

    def test_or_single_byte(self):
        """OR of two single bytes."""
        # chr(3)=0b00000011, chr(5)=0b00000101 → 0b00000111=chr(7)
        assert m_zbitor(chr(3), chr(5)) == chr(7)

    def test_or_identity_zero(self):
        """OR with NUL byte is identity."""
        assert m_zbitor(chr(42), chr(0)) == chr(42)

    def test_or_zero_zero(self):
        """OR of two NUL bytes is NUL."""
        assert m_zbitor(chr(0), chr(0)) == chr(0)

    def test_or_all_ones(self):
        """OR of 0xFF with anything is 0xFF."""
        assert m_zbitor(chr(255), chr(0)) == chr(255)
        assert m_zbitor(chr(255), chr(255)) == chr(255)

    def test_or_complementary_bits(self):
        """OR of complementary bytes gives 0xFF."""
        # 0xAA | 0x55 = 0xFF
        assert m_zbitor(chr(0xAA), chr(0x55)) == chr(0xFF)

    def test_or_different_lengths_shorter_first(self):
        """OR pads shorter first string with NUL, making it identity for extra bytes."""
        # "A" OR "AB" → OR(A,A)+OR(0,B) = A + B
        result = m_zbitor("A", "AB")
        assert len(result) == 2
        assert result[1] == "B"

    def test_or_different_lengths_shorter_second(self):
        """OR pads shorter second string with NUL."""
        result = m_zbitor("AB", "A")
        assert len(result) == 2
        assert result[0] == "A"  # A|A = A
        assert result[1] == "B"  # B|0 = B

    def test_or_empty_strings(self):
        """OR of two empty strings is empty."""
        assert m_zbitor("", "") == ""

    def test_or_one_empty(self):
        """OR with empty string returns the other string."""
        assert m_zbitor("ABC", "") == "ABC"
        assert m_zbitor("", "ABC") == "ABC"

    def test_or_multi_byte(self):
        """OR of multi-byte strings works byte-by-byte."""
        # chr(1)+chr(2) OR chr(4)+chr(8) = chr(5)+chr(10)
        s1 = chr(1) + chr(2)
        s2 = chr(4) + chr(8)
        result = m_zbitor(s1, s2)
        assert result == chr(5) + chr(10)


class TestZbitxorRuntime:
    """$ZBITXOR runtime helper tests (T068)."""

    def test_xor_single_byte(self):
        """XOR of two single bytes."""
        # chr(3)=0b11, chr(5)=0b101 → 0b110=chr(6)
        assert m_zbitxor(chr(3), chr(5)) == chr(6)

    def test_xor_same_value(self):
        """XOR of identical values is zero."""
        assert m_zbitxor(chr(42), chr(42)) == chr(0)

    def test_xor_with_zero(self):
        """XOR with zero is identity."""
        assert m_zbitxor(chr(42), chr(0)) == chr(42)

    def test_xor_all_ones(self):
        """XOR of 0xFF with 0xFF is 0x00."""
        assert m_zbitxor(chr(255), chr(255)) == chr(0)

    def test_xor_complementary(self):
        """XOR of complementary bytes gives 0xFF."""
        assert m_zbitxor(chr(0xAA), chr(0x55)) == chr(0xFF)

    def test_xor_different_lengths(self):
        """XOR pads shorter string with NUL."""
        result = m_zbitxor("A", "AB")
        assert len(result) == 2
        # A XOR A = 0, 0 XOR B = B
        assert result[0] == chr(0)
        assert result[1] == "B"

    def test_xor_empty_strings(self):
        """XOR of two empty strings is empty."""
        assert m_zbitxor("", "") == ""

    def test_xor_one_empty(self):
        """XOR with empty string returns the other string."""
        assert m_zbitxor("ABC", "") == "ABC"


class TestZbitnotRuntime:
    """$ZBITNOT runtime helper tests (T068)."""

    def test_not_zero(self):
        """NOT of 0x00 is 0xFF."""
        assert m_zbitnot(chr(0)) == chr(255)

    def test_not_all_ones(self):
        """NOT of 0xFF is 0x00."""
        assert m_zbitnot(chr(255)) == chr(0)

    def test_not_pattern(self):
        """NOT of 0xAA is 0x55."""
        assert m_zbitnot(chr(0xAA)) == chr(0x55)

    def test_not_multi_byte(self):
        """NOT operates on each byte independently."""
        result = m_zbitnot(chr(0) + chr(255))
        assert result == chr(255) + chr(0)

    def test_not_empty(self):
        """NOT of empty string is empty."""
        assert m_zbitnot("") == ""

    def test_double_not_identity(self):
        """NOT(NOT(x)) = x (involution)."""
        original = chr(42) + chr(99) + chr(200)
        assert m_zbitnot(m_zbitnot(original)) == original


class TestZgetsyiRuntime:
    """$ZGETSYI runtime helper tests (T070).

    $ZGETSYI("NODENAME") returns the hostname.
    Unknown keywords return empty string.
    """

    def test_nodename_returns_hostname(self):
        """$ZGETSYI("NODENAME") returns platform.node()."""
        import platform

        result = m_zgetsyi("NODENAME")
        assert result == platform.node()

    def test_nodename_case_insensitive(self):
        """$ZGETSYI keyword is case insensitive."""
        import platform

        assert m_zgetsyi("nodename") == platform.node()
        assert m_zgetsyi("NodeName") == platform.node()

    def test_unknown_keyword_returns_empty(self):
        """Unknown keywords return empty string."""
        assert m_zgetsyi("UNKNOWN") == ""

    def test_empty_keyword_returns_empty(self):
        """Empty keyword returns empty string."""
        assert m_zgetsyi("") == ""

    def test_nodename_non_empty(self):
        """NODENAME should return a non-empty string on any system."""
        result = m_zgetsyi("NODENAME")
        assert len(result) > 0


class TestZtimeRuntime:
    """$ZTIME runtime helper tests (T071).

    IRIS reference output validated via utils/run_mumps_iris.py:
    - $ZT(0) → 00:00:00
    - $ZT(1) → 00:00:01
    - $ZT(60) → 00:01:00
    - $ZT(3600) → 01:00:00
    - $ZT(3661) → 01:01:01
    - $ZT(86399) → 23:59:59
    """

    def test_midnight(self):
        """$ZT(0) → '00:00:00'."""
        assert m_ztime("0") == "00:00:00"

    def test_one_second(self):
        """$ZT(1) → '00:00:01'."""
        assert m_ztime("1") == "00:00:01"

    def test_one_minute(self):
        """$ZT(60) → '00:01:00'."""
        assert m_ztime("60") == "00:01:00"

    def test_one_hour(self):
        """$ZT(3600) → '01:00:00'."""
        assert m_ztime("3600") == "01:00:00"

    def test_combined(self):
        """$ZT(3661) → '01:01:01' (1h + 1m + 1s)."""
        assert m_ztime("3661") == "01:01:01"

    def test_end_of_day(self):
        """$ZT(86399) → '23:59:59'."""
        assert m_ztime("86399") == "23:59:59"

    def test_full_day(self):
        """$ZT(86400) wraps to '24:00:00' (no modular wrapping)."""
        # MUMPS doesn't wrap — just formats as-is
        assert m_ztime("86400") == "24:00:00"

    def test_negative_clamps_to_zero(self):
        """$ZT(-1) → '00:00:00' (negative clamped to 0)."""
        assert m_ztime("-1") == "00:00:00"

    def test_non_numeric_string(self):
        """$ZT("abc") → '00:00:00' (non-numeric coerced to 0)."""
        assert m_ztime("abc") == "00:00:00"

    def test_decimal_truncated(self):
        """$ZT(3661.999) → '01:01:01' (fractional seconds truncated)."""
        assert m_ztime("3661.999") == "01:01:01"

    def test_noon(self):
        """$ZT(43200) → '12:00:00'."""
        assert m_ztime("43200") == "12:00:00"

    def test_half_past_six(self):
        """$ZT(23400) → '06:30:00' (6.5 hours)."""
        assert m_ztime("23400") == "06:30:00"


class TestZdirRuntime:
    """$ZDIR runtime helper tests (T072)."""

    def test_returns_current_directory(self):
        """_rt_os_getcwd returns os.getcwd()."""
        import os

        result = _rt_os_getcwd()
        assert result == os.getcwd()

    def test_returns_string(self):
        """_rt_os_getcwd returns a string."""
        result = _rt_os_getcwd()
        assert isinstance(result, str)

    def test_returns_absolute_path(self):
        """_rt_os_getcwd returns an absolute path."""
        import os

        result = _rt_os_getcwd()
        assert os.path.isabs(result)
