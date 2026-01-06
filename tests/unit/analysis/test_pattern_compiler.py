"""Tests for MUMPS pattern to Python regex compiler.

Tests the compile_pattern_to_regex() function that converts MUMPS pattern
match expressions to equivalent Python regex patterns.

Reference: MUMPS 1995 ANSI Standard, Section 7.2.5
"""

import re

import pytest

from m2py.analysis.pattern_compiler import (
    compile_pattern_to_regex,
    PatternCompileError,
)


# =============================================================================
# Basic Pattern Codes
# =============================================================================


class TestBasicPatternCodes:
    """Test individual pattern codes."""

    def test_single_alpha(self):
        """Test single alphabetic character."""
        regex = compile_pattern_to_regex("1A")
        assert re.fullmatch(regex, "A")
        assert re.fullmatch(regex, "z")
        assert not re.fullmatch(regex, "1")
        assert not re.fullmatch(regex, " ")

    def test_single_numeric(self):
        """Test single numeric character."""
        regex = compile_pattern_to_regex("1N")
        assert re.fullmatch(regex, "5")
        assert re.fullmatch(regex, "0")
        assert not re.fullmatch(regex, "A")
        assert not re.fullmatch(regex, "-")

    def test_single_lowercase(self):
        """Test single lowercase alphabetic."""
        regex = compile_pattern_to_regex("1L")
        assert re.fullmatch(regex, "a")
        assert re.fullmatch(regex, "z")
        assert not re.fullmatch(regex, "A")
        assert not re.fullmatch(regex, "5")

    def test_single_uppercase(self):
        """Test single uppercase alphabetic."""
        regex = compile_pattern_to_regex("1U")
        assert re.fullmatch(regex, "A")
        assert re.fullmatch(regex, "Z")
        assert not re.fullmatch(regex, "a")
        assert not re.fullmatch(regex, "5")

    def test_single_everything(self):
        """Test single everything character."""
        regex = compile_pattern_to_regex("1E")
        assert re.fullmatch(regex, "A")
        assert re.fullmatch(regex, "5")
        assert re.fullmatch(regex, " ")
        assert re.fullmatch(regex, "#")

    def test_single_punctuation(self):
        """Test single punctuation character."""
        regex = compile_pattern_to_regex("1P")
        assert re.fullmatch(regex, " ")
        assert re.fullmatch(regex, "!")
        assert re.fullmatch(regex, "-")
        assert not re.fullmatch(regex, "A")
        assert not re.fullmatch(regex, "5")

    def test_single_control(self):
        """Test single control character."""
        regex = compile_pattern_to_regex("1C")
        assert re.fullmatch(regex, "\t")
        assert re.fullmatch(regex, "\n")
        assert re.fullmatch(regex, "\x00")
        assert not re.fullmatch(regex, "A")


# =============================================================================
# Repeat Counts
# =============================================================================


class TestRepeatCounts:
    """Test repeat count variations."""

    def test_exact_count(self):
        """Test exact count (3N = exactly 3 digits)."""
        regex = compile_pattern_to_regex("3N")
        assert re.fullmatch(regex, "123")
        assert re.fullmatch(regex, "000")
        assert not re.fullmatch(regex, "12")
        assert not re.fullmatch(regex, "1234")

    def test_zero_count(self):
        """Test zero count (0N = empty string)."""
        regex = compile_pattern_to_regex("0N")
        assert re.fullmatch(regex, "")
        assert not re.fullmatch(regex, "1")

    def test_any_count(self):
        """Test indefinite multiplier (.N = any number)."""
        regex = compile_pattern_to_regex(".N")
        assert re.fullmatch(regex, "")
        assert re.fullmatch(regex, "1")
        assert re.fullmatch(regex, "12345")

    def test_at_least(self):
        """Test at least n (2. = 2 or more)."""
        regex = compile_pattern_to_regex("2.N")
        assert not re.fullmatch(regex, "")
        assert not re.fullmatch(regex, "1")
        assert re.fullmatch(regex, "12")
        assert re.fullmatch(regex, "12345")

    def test_at_most(self):
        """Test at most n (.2N = 0 to 2)."""
        regex = compile_pattern_to_regex(".2N")
        assert re.fullmatch(regex, "")
        assert re.fullmatch(regex, "1")
        assert re.fullmatch(regex, "12")
        assert not re.fullmatch(regex, "123")

    def test_range(self):
        """Test range (2.4N = 2 to 4)."""
        regex = compile_pattern_to_regex("2.4N")
        assert not re.fullmatch(regex, "1")
        assert re.fullmatch(regex, "12")
        assert re.fullmatch(regex, "123")
        assert re.fullmatch(regex, "1234")
        assert not re.fullmatch(regex, "12345")


# =============================================================================
# Concatenated Patterns
# =============================================================================


class TestConcatenatedPatterns:
    """Test concatenated pattern atoms."""

    def test_letter_then_numbers(self):
        """Test 1A.N (one letter followed by any digits)."""
        regex = compile_pattern_to_regex("1A.N")
        assert re.fullmatch(regex, "A")
        assert re.fullmatch(regex, "A1")
        assert re.fullmatch(regex, "Z123")
        assert not re.fullmatch(regex, "1A")
        assert not re.fullmatch(regex, "")

    def test_phone_number_format(self):
        """Test phone number pattern (3N1"-"4N)."""
        regex = compile_pattern_to_regex('3N"-"4N')
        assert re.fullmatch(regex, "123-4567")
        assert not re.fullmatch(regex, "12-4567")
        assert not re.fullmatch(regex, "123-456")


# =============================================================================
# String Literals
# =============================================================================


class TestStringLiterals:
    """Test string literal patterns."""

    def test_simple_literal(self):
        """Test simple string literal."""
        regex = compile_pattern_to_regex('1"hello"')
        assert re.fullmatch(regex, "hello")
        assert not re.fullmatch(regex, "HELLO")

    def test_literal_with_special_chars(self):
        """Test literal with regex special characters."""
        regex = compile_pattern_to_regex('1"a.b*c"')
        assert re.fullmatch(regex, "a.b*c")
        assert not re.fullmatch(regex, "aXbXc")

    def test_escaped_quote(self):
        """Test escaped quote in literal."""
        regex = compile_pattern_to_regex('1"say ""hello"""')
        assert re.fullmatch(regex, 'say "hello"')


# =============================================================================
# Alternation
# =============================================================================


class TestAlternation:
    """Test alternation patterns."""

    def test_simple_alternation(self):
        """Test simple alternation (1N,1A) - either digit or letter."""
        regex = compile_pattern_to_regex("1(1N,1A)")
        assert re.fullmatch(regex, "5")
        assert re.fullmatch(regex, "A")
        assert not re.fullmatch(regex, " ")

    def test_three_way_alternation(self):
        """Test three-way alternation (1(1N,1A,1P)) - digit, letter, or punct.

        GAP-006: Coverage gap for lines 276-295 in pattern_compiler.py.
        """
        regex = compile_pattern_to_regex("1(1N,1A,1P)")
        assert re.fullmatch(regex, "5")
        assert re.fullmatch(regex, "A")
        assert re.fullmatch(regex, " ")
        assert re.fullmatch(regex, "!")

    def test_nested_alternation(self):
        """Test nested alternation (1(1(1N,1A),1P)) - nested parens.

        GAP-006: Coverage gap for nested paren tracking in pattern_compiler.py.
        """
        regex = compile_pattern_to_regex("1(1(1N,1A),1P)")
        assert re.fullmatch(regex, "5")
        assert re.fullmatch(regex, "A")
        assert re.fullmatch(regex, " ")

    def test_alternation_with_quoted_string(self):
        """Test alternation containing quoted string with comma.

        Pattern like 1("YES","NO") should match YES or NO, not treat
        the comma inside quotes as an alternation separator.

        GAP-006: Coverage gap for lines 299-315 in pattern_compiler.py.
        """
        regex = compile_pattern_to_regex('1("YES","NO")')
        assert re.fullmatch(regex, "YES")
        assert re.fullmatch(regex, "NO")
        assert not re.fullmatch(regex, "MAYBE")

    def test_alternation_with_escaped_quote(self):
        """Test alternation with escaped quote in string literal.

        Pattern like 1("a""b","c") should handle the "" escape properly.
        """
        regex = compile_pattern_to_regex('1("a""b","c")')
        assert re.fullmatch(regex, 'a"b')
        assert re.fullmatch(regex, "c")

    def test_alternation_with_multiple_atoms(self):
        """Test alternation where alternatives have multiple atoms.

        Pattern like 1(2N"-"4N,8N) - SSN format OR 8-digit number.
        """
        regex = compile_pattern_to_regex('1(3N"-"4N,8N)')
        assert re.fullmatch(regex, "123-4567")
        assert re.fullmatch(regex, "12345678")
        assert not re.fullmatch(regex, "12-4567")


# =============================================================================
# Real-World Patterns
# =============================================================================


class TestRealWorldPatterns:
    """Test patterns from real MUMPS code."""

    def test_identifier_pattern(self):
        """Test MUMPS identifier pattern (1A.AN)."""
        regex = compile_pattern_to_regex("1A.AN")
        assert re.fullmatch(regex, "X")
        assert re.fullmatch(regex, "VAR1")
        assert re.fullmatch(regex, "Test123")
        assert not re.fullmatch(regex, "1VAR")
        assert not re.fullmatch(regex, "")

    def test_numeric_literal_pattern(self):
        """Test numeric with optional decimal (.N.1".".N)."""
        regex = compile_pattern_to_regex('.N.1".".N')
        assert re.fullmatch(regex, "123")
        assert re.fullmatch(regex, "123.45")
        assert re.fullmatch(regex, ".5")
        assert re.fullmatch(regex, "")

    def test_any_string(self):
        """Test any string pattern (.E)."""
        regex = compile_pattern_to_regex(".E")
        assert re.fullmatch(regex, "")
        assert re.fullmatch(regex, "anything goes here 123!@#")


# =============================================================================
# Case Insensitivity
# =============================================================================


class TestCaseInsensitivity:
    """Test that pattern codes are case-insensitive."""

    def test_lowercase_patcode(self):
        """Test lowercase pattern codes work same as uppercase."""
        regex_upper = compile_pattern_to_regex("1A")
        regex_lower = compile_pattern_to_regex("1a")
        assert re.fullmatch(regex_upper, "X")
        assert re.fullmatch(regex_lower, "X")


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_pattern(self):
        """Test empty pattern returns empty regex."""
        assert compile_pattern_to_regex("") == ""

    def test_unterminated_string(self):
        """Test unterminated string literal raises error."""
        with pytest.raises(PatternCompileError):
            compile_pattern_to_regex('1"hello')

    def test_invalid_patcode(self):
        """Test invalid pattern code raises error."""
        with pytest.raises(PatternCompileError):
            compile_pattern_to_regex("1X")


# =============================================================================
# ASG Integration
# =============================================================================


@pytest.mark.asg
class TestPatternMatchASGIntegration:
    """Test MPatternMatch.compiled_regex field behavior in ASG."""

    def test_compiled_regex_populated_for_simple_pattern(self):
        """Pattern match with simple pattern should have compiled_regex populated."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse('TEST\n I X?1N W "num"\n')

        # Find the IF statement
        label = routine.labels[0]
        stmt = label.body.statements[0]

        # The condition should be an MPatternMatch
        from m2py.asg.expressions import MPatternMatch

        assert isinstance(stmt.condition, MPatternMatch)
        assert stmt.condition.pattern == "1N"
        assert stmt.condition.compiled_regex == "[0-9]"

    def test_compiled_regex_none_for_indirect_pattern(self):
        """Indirect pattern (?@VAR) should have compiled_regex=None.

        Indirect patterns cannot be pre-compiled because the pattern value
        is determined at runtime. The semantic analyzer gracefully leaves
        compiled_regex as None in these cases.
        """
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse('TEST\n I X?@PAT W "match"\n')

        # Find the IF statement
        label = routine.labels[0]
        stmt = label.body.statements[0]

        # The condition should be an MPatternMatch with indirect pattern
        from m2py.asg.expressions import MPatternMatch

        assert isinstance(stmt.condition, MPatternMatch)
        # Indirect patterns have pattern_indirect set
        assert stmt.condition.pattern_indirect is not None
        # compiled_regex should be None since pattern is runtime-determined
        assert stmt.condition.compiled_regex is None
