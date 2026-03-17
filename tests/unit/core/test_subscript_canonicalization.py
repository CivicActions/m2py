"""Unit tests for subscript canonicalization behavior.

Tests that subscripts canonicalize so A(1), A(01), A(1.0), A("1") all
reference the same node, while A("01") is DISTINCT from A(1).

Feature: 018-unified-variable-system
User Story: US4 - Subscript Canonicalization
Requirements: FR-003, FR-004
"""

from m2py.core.subscripts import SubscriptCanonicalizer
from m2py.runtime import MArray


class TestNumericSubscriptsSameNode:
    """T064: Test that A(1) vs A(01) vs A(1.0) vs A("1") all reference same node."""

    def test_integer_and_canonical_string_same_node(self):
        """A(1) and A("1") access the same node."""
        arr = MArray()
        arr[1] = "value"
        assert arr.get("1") == "value"
        assert arr.get(1) == "value"

    def test_float_equal_to_int_same_node(self):
        """A(1.0) and A(1) access the same node."""
        arr = MArray()
        arr[1.0] = "from_float"
        assert arr.get(1) == "from_float"
        assert arr.get("1") == "from_float"

    def test_set_via_int_read_via_float(self):
        """Set via A(1), read via A(1.0)."""
        arr = MArray()
        arr[1] = "from_int"
        assert arr.get(1.0) == "from_int"

    def test_set_via_canonical_string_read_via_int(self):
        """Set via A("1"), read via A(1)."""
        arr = MArray()
        arr["1"] = "from_string"
        assert arr.get(1) == "from_string"
        assert arr.get(1.0) == "from_string"

    def test_numeric_canonicalization_python_literal_01(self):
        """Python numeric literal that equals 1 canonicalizes to 1.

        Note: In Python 3, 01 is a syntax error. This tests the concept
        that any int with value 1 canonicalizes the same.
        """
        arr = MArray()
        arr[1] = "value"
        # Python literal 01 is just 1
        assert arr.get(int("01")) == "value"


class TestNonCanonicalStringsDifferentNodes:
    """T065: Test that A("01") is DISTINCT from A(1) (non-canonical string preserved)."""

    def test_leading_zero_string_different_from_int(self):
        """A("01") is different from A(1)."""
        arr = MArray()
        arr[1] = "integer_value"
        arr["01"] = "string_with_leading_zero"

        assert arr.get(1) == "integer_value"
        assert arr.get("01") == "string_with_leading_zero"
        assert arr.get(1) != arr.get("01")

    def test_trailing_zero_string_different_from_int(self):
        """A("1.0") is different from A(1)."""
        arr = MArray()
        arr[1] = "integer_value"
        arr["1.0"] = "string_with_trailing_zero"

        assert arr.get(1) == "integer_value"
        assert arr.get("1.0") == "string_with_trailing_zero"

    def test_leading_zero_decimal_different(self):
        """A("0.5") is different from A(.5)."""
        arr = MArray()
        arr[0.5] = "float_value"  # Canonicalizes to ".5"
        arr["0.5"] = "string_with_leading_zero"

        assert arr.get(0.5) == "float_value"
        assert arr.get(".5") == "float_value"  # Canonical form
        assert arr.get("0.5") == "string_with_leading_zero"

    def test_multiple_leading_zeros(self):
        """A("001") is different from A(1)."""
        arr = MArray()
        arr[1] = "integer_value"
        arr["001"] = "triple_leading_zeros"

        assert arr.get(1) == "integer_value"
        assert arr.get("001") == "triple_leading_zeros"


class TestDecimalCanonicalForms:
    """Test decimal subscript canonicalization."""

    def test_half_canonical_forms(self):
        """0.5 and .5 are the same in canonical form."""
        arr = MArray()
        arr[0.5] = "half"

        # Float 0.5 canonicalizes to ".5"
        assert arr.get(".5") == "half"
        assert arr.get(0.5) == "half"

    def test_negative_decimal_canonical_form(self):
        """-0.5 canonicalizes to -.5."""
        arr = MArray()
        arr[-0.5] = "negative_half"

        assert arr.get("-.5") == "negative_half"
        assert arr.get(-0.5) == "negative_half"

    def test_trailing_zeros_on_decimal(self):
        """1.50 canonicalizes to 1.5."""
        arr = MArray()
        arr[1.5] = "one_and_half"

        assert arr.get("1.5") == "one_and_half"
        # Python float 1.50 == 1.5
        assert arr.get(1.50) == "one_and_half"


class TestMultipleSubscripts:
    """Test canonicalization with multiple subscripts."""

    def test_multiple_subscripts_all_canonical(self):
        """Multiple canonical subscripts access same node."""
        arr = MArray()
        arr[1, 2, 3] = "deep_value"

        # Various equivalent forms
        assert arr.get(1, 2, 3) == "deep_value"
        assert arr.get("1", "2", "3") == "deep_value"
        assert arr.get(1.0, 2.0, 3.0) == "deep_value"
        assert arr.get(1, "2", 3.0) == "deep_value"

    def test_multiple_subscripts_non_canonical_middle(self):
        """Non-canonical subscript in the middle creates different node."""
        arr = MArray()
        arr[1, 2, 3] = "canonical"
        arr[1, "02", 3] = "non_canonical_middle"

        assert arr.get(1, 2, 3) == "canonical"
        assert arr.get(1, "02", 3) == "non_canonical_middle"

    def test_getitem_subscript_canonicalization(self):
        """__getitem__ with tuple also canonicalizes."""
        arr = MArray()
        arr[1, 2] = "value"

        # Use __getitem__ notation
        assert arr[1, 2].value == "value"
        assert arr["1", "2"].value == "value"
        assert arr[1.0, 2.0].value == "value"


class TestSubscriptCanonicalizerIntegration:
    """Test that MArray uses SubscriptCanonicalizer correctly."""

    def test_canonicalizer_consistency_integers(self):
        """MArray canonicalization matches SubscriptCanonicalizer for integers."""
        # What SubscriptCanonicalizer says
        assert SubscriptCanonicalizer.canonicalize(1) == "1"
        assert SubscriptCanonicalizer.canonicalize(0) == "0"
        assert SubscriptCanonicalizer.canonicalize(-42) == "-42"

        # MArray should produce same keys
        arr = MArray()
        arr[1] = "one"
        arr[0] = "zero"
        arr[-42] = "neg42"

        assert arr.get("1") == "one"
        assert arr.get("0") == "zero"
        assert arr.get("-42") == "neg42"

    def test_canonicalizer_consistency_floats(self):
        """MArray canonicalization matches SubscriptCanonicalizer for floats."""
        assert SubscriptCanonicalizer.canonicalize(1.0) == "1"
        assert SubscriptCanonicalizer.canonicalize(1.5) == "1.5"
        assert SubscriptCanonicalizer.canonicalize(0.5) == ".5"

        arr = MArray()
        arr[1.0] = "one"
        arr[1.5] = "one_five"
        arr[0.5] = "half"

        assert arr.get("1") == "one"
        assert arr.get("1.5") == "one_five"
        assert arr.get(".5") == "half"

    def test_canonicalizer_preserves_non_canonical_strings(self):
        """Non-canonical strings are preserved, not converted."""
        # SubscriptCanonicalizer preserves these
        assert SubscriptCanonicalizer.canonicalize("01") == "01"
        assert SubscriptCanonicalizer.canonicalize("1.0") == "1.0"
        assert SubscriptCanonicalizer.canonicalize("ABC") == "ABC"

        # MArray should store with these exact keys
        arr = MArray()
        arr["01"] = "zero_one"
        arr["1.0"] = "one_point_zero"
        arr["ABC"] = "abc"

        assert arr.get("01") == "zero_one"
        assert arr.get("1.0") == "one_point_zero"
        assert arr.get("ABC") == "abc"

        # They should NOT be same as canonical forms
        assert arr.get(1) != "zero_one"  # 1 != "01"
        assert arr.get(1) != "one_point_zero"  # 1 != "1.0"


class TestEdgeCases:
    """Edge cases from YDB verification."""

    def test_negative_zero(self):
        """Negative zero canonicalizes to 0."""
        arr = MArray()
        arr[0] = "zero"
        # Python -0.0 == 0.0, so should access same node
        assert arr.get(-0.0) == "zero"

    def test_very_small_decimal(self):
        """Very small decimals canonicalize correctly."""
        arr = MArray()
        arr[0.001] = "small"
        assert arr.get(".001") == "small"

    def test_subscript_with_spaces(self):
        """Strings with spaces are preserved exactly."""
        arr = MArray()
        arr[" 1"] = "space_one"
        arr["1 "] = "one_space"
        arr[" 1 "] = "spaces"

        assert arr.get(" 1") == "space_one"
        assert arr.get("1 ") == "one_space"
        assert arr.get(" 1 ") == "spaces"

        # These are all different from numeric 1
        assert arr.get(1) == ""  # Not found

    def test_scientific_notation_string(self):
        """Scientific notation strings are NOT canonical."""
        arr = MArray()
        arr["1E2"] = "scientific"
        arr[100] = "hundred"

        # They are different nodes
        assert arr.get("1E2") == "scientific"
        assert arr.get(100) == "hundred"


class TestSubscriptCanonicalizationEdges:
    """Tests for subscript canonicalization LIVE edge cases."""

    def test_numeric_string(self):
        """Numeric string canonicalizes to canonical string."""
        assert SubscriptCanonicalizer.canonicalize("42") == "42"
        assert SubscriptCanonicalizer.canonicalize("3.14") == "3.14"

    def test_non_numeric_string(self):
        """Non-numeric string stays as string."""
        assert SubscriptCanonicalizer.canonicalize("hello") == "hello"

    def test_leading_zero_string(self):
        """Leading zero makes it non-canonical number."""
        result = SubscriptCanonicalizer.canonicalize("007")
        # "007" is not canonical numeric form, but m_num("007") = 7
        assert result is not None

    def test_empty_string(self):
        """Empty string canonicalizes to empty string."""
        assert SubscriptCanonicalizer.canonicalize("") == ""

    def test_integer_passthrough(self):
        """Integer value becomes canonical string."""
        assert SubscriptCanonicalizer.canonicalize(42) == "42"


# =============================================================================
# indirection.py: LIVE edge cases
# =============================================================================
