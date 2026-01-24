"""Tests for runtime label validation and translation functions.

Tests the _is_valid_label and _translate_label_to_func functions that
support indirect DO/GOTO to numeric and %-prefixed labels.

Reference: MUMPS labels can be numeric (e.g., 461, 123) or start with %,
which requires translation to valid Python function names.
"""

from m2py.runtime import _is_valid_label, _translate_label_to_func


# =============================================================================
# _is_valid_label Tests
# =============================================================================


class TestIsValidLabel:
    """Tests for _is_valid_label function."""

    def test_valid_alpha_label(self):
        """Standard alphabetic label is valid."""
        assert _is_valid_label("ENTRY") is True

    def test_valid_mixed_case(self):
        """Mixed case label is valid."""
        assert _is_valid_label("MyLabel") is True

    def test_valid_numeric_label(self):
        """Purely numeric label is valid (MUMPS allows this)."""
        assert _is_valid_label("461") is True

    def test_valid_numeric_label_leading_zero(self):
        """Numeric label with leading zero is valid."""
        assert _is_valid_label("0123") is True

    def test_valid_single_digit(self):
        """Single digit label is valid."""
        assert _is_valid_label("1") is True

    def test_valid_percent_prefix(self):
        """%-prefixed label is valid."""
        assert _is_valid_label("%BREAK") is True

    def test_valid_percent_alone(self):
        """% alone is a valid label."""
        assert _is_valid_label("%") is True

    def test_valid_alphanumeric(self):
        """Alphanumeric label is valid."""
        assert _is_valid_label("LABEL1") is True
        assert _is_valid_label("A1B2C3") is True

    def test_valid_starts_with_digit_then_alpha(self):
        """Label starting with digit then alpha is valid."""
        assert _is_valid_label("1ABC") is True

    def test_invalid_empty_string(self):
        """Empty string is not a valid label."""
        assert _is_valid_label("") is False

    def test_invalid_special_characters(self):
        """Special characters make label invalid."""
        assert _is_valid_label("LABEL-1") is False
        assert _is_valid_label("LABEL_1") is False
        assert _is_valid_label("LABEL.1") is False
        assert _is_valid_label("LABEL!") is False

    def test_invalid_spaces(self):
        """Spaces make label invalid."""
        assert _is_valid_label("MY LABEL") is False
        assert _is_valid_label(" LABEL") is False
        assert _is_valid_label("LABEL ") is False

    def test_invalid_caret(self):
        """Caret (^) makes label invalid (that's for globals)."""
        assert _is_valid_label("^ROUTINE") is False

    def test_invalid_at_sign(self):
        """At sign (@) makes label invalid."""
        assert _is_valid_label("@LABEL") is False


# =============================================================================
# _translate_label_to_func Tests
# =============================================================================


class TestTranslateLabelToFunc:
    """Tests for _translate_label_to_func function."""

    def test_translate_standard_label(self):
        """Standard alpha label unchanged."""
        assert _translate_label_to_func("ENTRY") == "ENTRY"

    def test_translate_alphanumeric(self):
        """Alphanumeric label unchanged."""
        assert _translate_label_to_func("LABEL1") == "LABEL1"

    def test_translate_numeric_label(self):
        """Numeric label gets _n_ prefix."""
        assert _translate_label_to_func("461") == "_n_461"

    def test_translate_single_digit(self):
        """Single digit gets _n_ prefix."""
        assert _translate_label_to_func("1") == "_n_1"

    def test_translate_numeric_leading_zero(self):
        """Numeric with leading zero gets prefix."""
        assert _translate_label_to_func("0123") == "_n_0123"

    def test_translate_percent_prefix(self):
        """%-prefixed label gets _pct_ translation."""
        assert _translate_label_to_func("%BREAK") == "_pct_BREAK"

    def test_translate_percent_alone(self):
        """% alone becomes _pct_."""
        assert _translate_label_to_func("%") == "_pct_"

    def test_translate_percent_with_numbers(self):
        """%123 becomes _pct_123."""
        assert _translate_label_to_func("%123") == "_pct_123"

    def test_translate_empty_string(self):
        """Empty string returns empty."""
        assert _translate_label_to_func("") == ""

    def test_translate_none_like_empty(self):
        """Edge case: None should be handled gracefully (if passed as string)."""
        # The function signature takes str, but edge case testing is valuable
        # In practice, callers should ensure str type
        pass  # Skipped - function requires str type

    def test_translate_lowercase_preserved(self):
        """Lowercase letters preserved."""
        assert _translate_label_to_func("mylabel") == "mylabel"

    def test_translate_mixed_case_preserved(self):
        """Mixed case preserved."""
        assert _translate_label_to_func("MyLabel") == "MyLabel"

    def test_translate_digit_in_middle_unchanged(self):
        """Digit in middle doesn't affect translation."""
        assert _translate_label_to_func("A1B") == "A1B"


# =============================================================================
# Integration Tests
# =============================================================================


class TestLabelValidationTranslationIntegration:
    """Integration tests combining validation and translation."""

    def test_valid_label_translates(self):
        """All valid labels should translate without error."""
        valid_labels = ["ENTRY", "1", "461", "%BREAK", "%", "A1B2"]
        for label in valid_labels:
            assert _is_valid_label(label), f"{label} should be valid"
            result = _translate_label_to_func(label)
            assert result, f"{label} should translate to non-empty"
            # Translation result should be a valid Python identifier
            assert result.isidentifier() or result.startswith("_"), (
                f"{label} -> {result} should be valid Python identifier"
            )

    def test_numeric_labels_round_trip(self):
        """Numeric labels common in MUMPS code."""
        numeric_labels = ["1", "10", "100", "461", "462", "0"]
        for label in numeric_labels:
            assert _is_valid_label(label)
            py_name = _translate_label_to_func(label)
            assert py_name.startswith("_n_")
            assert py_name == f"_n_{label}"

    def test_percent_labels_round_trip(self):
        """%-prefixed labels common in MUMPS utilities."""
        pct_labels = ["%", "%X", "%BREAK", "%UTIL", "%ZTS"]
        for label in pct_labels:
            assert _is_valid_label(label)
            py_name = _translate_label_to_func(label)
            assert py_name.startswith("_pct_")
