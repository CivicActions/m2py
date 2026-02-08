"""Tests for parse_call_target method and CallTarget handling.

Tests the parse_call_target method that parses DO/GOTO indirection targets
into their components (label, routine, offset). Includes support for
numeric labels which are valid in MUMPS but not covered by basic tests.

Reference: MUMPS labels can be purely numeric (1, 461, etc.) which requires
special handling in parse_call_target.
"""

import pytest
from m2py.runtime import MUMPSRuntime, CallTarget, IndirectionError


# =============================================================================
# parse_call_target Basic Tests
# =============================================================================


class TestParseCallTargetBasic:
    """Basic tests for parse_call_target method."""

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_simple_label(self, rt):
        """Simple label like ENTRY."""
        result = rt.parse_call_target("ENTRY")
        assert result == CallTarget(label="ENTRY", routine=None, offset=None)

    def test_label_with_routine(self, rt):
        """Label with routine: LABEL^ROUTINE."""
        result = rt.parse_call_target("LABEL^ROUTINE")
        assert result == CallTarget(label="LABEL", routine="ROUTINE", offset=None)

    def test_label_with_offset_and_routine(self, rt):
        """Label with offset and routine: LABEL+5^ROUTINE."""
        result = rt.parse_call_target("LABEL+5^ROUTINE")
        assert result == CallTarget(label="LABEL", routine="ROUTINE", offset=5)

    def test_just_routine(self, rt):
        """Just routine: ^ROUTINE."""
        result = rt.parse_call_target("^ROUTINE")
        assert result == CallTarget(label=None, routine="ROUTINE", offset=None)

    def test_offset_only_with_routine(self, rt):
        """Offset only with routine: +5^ROUTINE."""
        result = rt.parse_call_target("+5^ROUTINE")
        assert result == CallTarget(label=None, routine="ROUTINE", offset=5)

    def test_empty_raises(self, rt):
        """Empty string raises IndirectionError."""
        with pytest.raises(IndirectionError):
            rt.parse_call_target("")

    def test_none_like_empty_raises(self, rt):
        """None converted to empty string raises error."""
        with pytest.raises(IndirectionError):
            rt.parse_call_target(None)


# =============================================================================
# Numeric Label Support Tests
# =============================================================================


class TestParseCallTargetNumericLabels:
    """Tests for numeric label support in parse_call_target."""

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_numeric_label_string(self, rt):
        """Numeric label passed as string: "461"."""
        result = rt.parse_call_target("461")
        assert result == CallTarget(label="461", routine=None, offset=None)

    def test_numeric_label_integer(self, rt):
        """Numeric label passed as integer: 461.

        MUMPS is polymorphic - S A=1 D @A should call label "1".
        """
        result = rt.parse_call_target(1)
        assert result == CallTarget(label="1", routine=None, offset=None)

    def test_single_digit_label(self, rt):
        """Single digit label: "1"."""
        result = rt.parse_call_target("1")
        assert result == CallTarget(label="1", routine=None, offset=None)

    def test_leading_zero_label(self, rt):
        """Label with leading zero: "0123"."""
        result = rt.parse_call_target("0123")
        assert result == CallTarget(label="0123", routine=None, offset=None)

    def test_numeric_label_with_routine(self, rt):
        """Numeric label with routine: 1^ROUTINE."""
        result = rt.parse_call_target("1^ROUTINE")
        assert result == CallTarget(label="1", routine="ROUTINE", offset=None)

    def test_numeric_label_with_offset(self, rt):
        """Numeric label with offset: 1+5^ROUTINE."""
        result = rt.parse_call_target("1+5^ROUTINE")
        assert result == CallTarget(label="1", routine="ROUTINE", offset=5)


# =============================================================================
# %-Prefixed Label Tests
# =============================================================================


class TestParseCallTargetPercentLabels:
    """Tests for %-prefixed labels in parse_call_target."""

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_percent_label(self, rt):
        """%-prefixed label: %BREAK."""
        result = rt.parse_call_target("%BREAK")
        assert result == CallTarget(label="%BREAK", routine=None, offset=None)

    def test_percent_alone(self, rt):
        """% alone is a valid label."""
        result = rt.parse_call_target("%")
        assert result == CallTarget(label="%", routine=None, offset=None)

    def test_percent_with_routine(self, rt):
        """%-prefixed label with routine."""
        result = rt.parse_call_target("%UTIL^ROUTINE")
        assert result == CallTarget(label="%UTIL", routine="ROUTINE", offset=None)

    def test_percent_routine_name(self, rt):
        """Routine name starting with %."""
        result = rt.parse_call_target("LABEL^%ROUTINE")
        assert result == CallTarget(label="LABEL", routine="%ROUTINE", offset=None)


# =============================================================================
# Error Cases Tests
# =============================================================================


class TestParseCallTargetErrors:
    """Tests for error handling in parse_call_target."""

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_empty_routine_after_caret(self, rt):
        """Empty routine after ^ raises error."""
        with pytest.raises(IndirectionError) as exc_info:
            rt.parse_call_target("LABEL^")
        assert "empty routine name" in str(exc_info.value)

    def test_invalid_routine_name(self, rt):
        """Invalid routine name raises error."""
        with pytest.raises(IndirectionError) as exc_info:
            rt.parse_call_target("LABEL^123INVALID")
        # Routine names must start with alpha or %
        assert "invalid routine name" in str(exc_info.value)

    def test_invalid_offset_not_integer(self, rt):
        """Non-integer offset raises error."""
        with pytest.raises(IndirectionError) as exc_info:
            rt.parse_call_target("LABEL+ABC^ROUTINE")
        assert "invalid offset" in str(exc_info.value)

    def test_invalid_label_special_chars(self, rt):
        """Label with special characters raises error."""
        with pytest.raises(IndirectionError) as exc_info:
            rt.parse_call_target("LABEL-NAME")
        assert "invalid label name" in str(exc_info.value)

    def test_whitespace_stripped(self, rt):
        """Whitespace is stripped from input."""
        result = rt.parse_call_target("  LABEL  ")
        assert result == CallTarget(label="LABEL", routine=None, offset=None)


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestParseCallTargetEdgeCases:
    """Edge case tests for parse_call_target."""

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_zero_offset(self, rt):
        """Offset of zero is valid."""
        result = rt.parse_call_target("LABEL+0^ROUTINE")
        assert result == CallTarget(label="LABEL", routine="ROUTINE", offset=0)

    def test_negative_offset(self, rt):
        """Negative offset is parsed (though unusual)."""
        result = rt.parse_call_target("LABEL+-1^ROUTINE")
        # This parses but -1 is unusual; implementation may vary
        assert result.offset == -1

    def test_large_offset(self, rt):
        """Large offset value."""
        result = rt.parse_call_target("LABEL+999^ROUTINE")
        assert result.offset == 999

    def test_mixed_case_label(self, rt):
        """Mixed case label preserved."""
        result = rt.parse_call_target("MyLabel")
        assert result.label == "MyLabel"

    def test_alphanumeric_label(self, rt):
        """Alphanumeric label: A1B2."""
        result = rt.parse_call_target("A1B2")
        assert result.label == "A1B2"

    def test_float_input_converted(self, rt):
        """Float input converted to string - 1.0 becomes "1.0" (invalid label)."""
        # 1.0 as string is "1.0", which is not a valid label
        with pytest.raises(IndirectionError):
            rt.parse_call_target(1.0)  # "1.0" is invalid
        # Fractional floats are also invalid
        with pytest.raises(IndirectionError):
            rt.parse_call_target(1.5)  # "1.5" is invalid


# =============================================================================
# Integration with resolve_nested_indirection
# =============================================================================


class TestParseCallTargetWithResolvedIndirection:
    """Integration tests with indirection resolution."""

    @pytest.fixture
    def rt(self):
        """Create a fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_resolved_label_parsed(self, rt):
        """Resolved indirection value parsed correctly."""
        # Simulates D @A where A="LABEL"
        # First resolve then parse
        target = "LABEL"  # After resolution
        result = rt.parse_call_target(target)
        assert result.label == "LABEL"

    def test_resolved_numeric_label(self, rt):
        """Resolved numeric value parsed correctly."""
        # Simulates D @A where A=1
        # After resolution, we get "1" or 1
        result = rt.parse_call_target(1)
        assert result.label == "1"
