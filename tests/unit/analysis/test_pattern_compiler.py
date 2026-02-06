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

    @pytest.mark.parametrize(
        "pattern,valid_chars,invalid_chars",
        [
            pytest.param("1A", ["A", "z"], ["1", " "], id="alpha"),
            pytest.param("1N", ["5", "0"], ["A", "-"], id="numeric"),
            pytest.param("1L", ["a", "z"], ["A", "5"], id="lowercase"),
            pytest.param("1U", ["A", "Z"], ["a", "5"], id="uppercase"),
            pytest.param("1E", ["A", "5", " ", "#"], [], id="everything"),
            pytest.param("1P", [" ", "!", "-"], ["A", "5"], id="punctuation"),
            pytest.param("1C", ["\t", "\n", "\x00"], ["A"], id="control"),
        ],
    )
    def test_single_pattern_code(self, pattern, valid_chars, invalid_chars):
        """Test single character pattern codes (1A, 1N, 1L, 1U, 1E, 1P, 1C)."""
        regex = compile_pattern_to_regex(pattern)
        for char in valid_chars:
            assert re.fullmatch(regex, char), f"{pattern} should match '{repr(char)}'"
        for char in invalid_chars:
            assert not re.fullmatch(regex, char), (
                f"{pattern} should not match '{repr(char)}'"
            )


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

    def test_empty_string_literal(self):
        """Test empty string literal pattern.

        Per MUMPS standard, patterns with empty string literals only match
        the empty string regardless of repeat count. The empty string literal
        can only match zero characters, so any count of it still matches zero.

        YDB behavior verified:
          ""?."" → 1 (empty matches any count of empty strings)
          "A"?."" → 0 (non-empty cannot match empty string literal)
          ""?0"" → 1 (zero occurrences matches empty)
          ""?.11"" → 1 (0-11 occurrences matches empty)
        """
        # .""  - any number of empty strings (matches only empty string)
        regex = compile_pattern_to_regex('.""')
        assert regex == ""  # Empty regex matches only empty via fullmatch
        assert re.fullmatch(regex, "")
        assert not re.fullmatch(regex, "A")
        assert not re.fullmatch(regex, "hello")

        # 0"" - zero empty strings (matches only empty string)
        regex = compile_pattern_to_regex('0""')
        assert regex == ""
        assert re.fullmatch(regex, "")
        assert not re.fullmatch(regex, "X")

        # .11"" - 0 to 11 empty strings (matches only empty string)
        regex = compile_pattern_to_regex('.11""')
        assert regex == ""
        assert re.fullmatch(regex, "")
        assert not re.fullmatch(regex, "X")

        # 1"" - exactly one empty string (matches only empty string)
        regex = compile_pattern_to_regex('1""')
        assert regex == ""
        assert re.fullmatch(regex, "")
        assert not re.fullmatch(regex, "A")

    def test_empty_string_literal_in_sequence(self):
        """Test empty string literal combined with other patterns.

        Pattern like 1N."" should match a single digit (the empty string
        literal adds nothing to the match).
        """
        # 1N."" - one digit followed by any number of empty strings
        regex = compile_pattern_to_regex('1N.""')
        assert re.fullmatch(regex, "5")
        assert re.fullmatch(regex, "0")
        assert not re.fullmatch(regex, "55")
        assert not re.fullmatch(regex, "A")
        assert not re.fullmatch(regex, "")

        # .""1A - any empty strings followed by one alpha
        regex = compile_pattern_to_regex('.""1A')
        assert re.fullmatch(regex, "A")
        assert re.fullmatch(regex, "z")
        assert not re.fullmatch(regex, "5")
        assert not re.fullmatch(regex, "")


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
# Group Quantification (Phase 22 - T127)
# =============================================================================


class TestGroupQuantification:
    """Test that quantified groups wrap in (?:...) to avoid double quantifiers.

    Phase 22 fix: Patterns like 2(5NA) were generating [0-9A-Za-z]{5}{2}
    which is invalid regex (multiple repeat). Must generate (?:[0-9A-Za-z]{5}){2}.
    """

    def test_quantified_group_basic(self):
        """Test 2(5NA) - 2 repetitions of 5 alphanumeric chars."""
        regex = compile_pattern_to_regex("2(5NA)")
        assert re.fullmatch(regex, "ABC12ABC12")
        assert not re.fullmatch(regex, "ABC12")

    def test_quantified_group_with_unbounded(self):
        """Test 2(.A) - group with 0+ alpha repeated 2 times."""
        regex = compile_pattern_to_regex("2(.A)")
        assert re.fullmatch(regex, "")
        assert re.fullmatch(regex, "ABC")
        # Can't distinguish between 2 groups of 0+ - always matches

    def test_quantified_group_range(self):
        """Test 2(1.3AN) - group with 1-3 alphanumeric, repeated 2 times."""
        regex = compile_pattern_to_regex("2(1.3AN)")
        # "AB12m" = 2 matched as group "AB" + "12m" (each 1-3 AN)
        assert re.fullmatch(regex, "AB12m")
        # Must have at least 2 chars (2 groups x 1 min each)
        assert not re.fullmatch(regex, "")

    def test_quantified_group_string_literal(self):
        """Test .4(2\"1A\") - group with string literal, repeated 0-4 times."""
        regex = compile_pattern_to_regex('.4(2"1A")')
        assert re.fullmatch(regex, "")
        assert re.fullmatch(regex, "1A1A")
        assert not re.fullmatch(regex, "1A1A1A1A1A1A1A1A1A")

    def test_unquantified_group_no_wrapping(self):
        """Test 1(5NA) - exactly 1 repetition doesn't need wrapping."""
        regex = compile_pattern_to_regex("1(5NA)")
        assert re.fullmatch(regex, "ABC12")
        assert not re.fullmatch(regex, "ABC12ABC12")

    def test_regex_validity_v4pat_patterns(self):
        """Verify all V4PAT1 patterns produce valid regex (no multiple repeat)."""
        patterns = [
            "2(5NA)",
            "2(.A)",
            "2(2.NU)",
            "2(1.3AN)",
            ".4(3.UPN)",
            ".5(1.4ANP)",
        ]
        for pattern in patterns:
            regex = compile_pattern_to_regex(pattern)
            # This should not raise re.error
            re.compile(regex)

    def test_zero_quantified_group(self):
        """Test 0(5NA) - 0 repetitions should match only empty string."""
        regex = compile_pattern_to_regex("0(5NA)")
        assert re.fullmatch(regex, "")
        assert not re.fullmatch(regex, "ABC12")

    def test_at_least_quantified_group(self):
        """Test 2.(3N) - 2 or more groups of exactly 3 digits."""
        regex = compile_pattern_to_regex("2.(3N)")
        assert not re.fullmatch(regex, "123")  # Only 1 group
        assert re.fullmatch(regex, "123456")  # 2 groups
        assert re.fullmatch(regex, "123456789")  # 3 groups

    def test_at_most_quantified_group(self):
        """Test .3(2N) - 0 to 3 groups of exactly 2 digits."""
        regex = compile_pattern_to_regex(".3(2N)")
        assert re.fullmatch(regex, "")  # 0 groups
        assert re.fullmatch(regex, "12")  # 1 group
        assert re.fullmatch(regex, "1234")  # 2 groups
        assert re.fullmatch(regex, "123456")  # 3 groups
        assert not re.fullmatch(regex, "12345678")  # 4 groups

    def test_quantified_group_with_alternation(self):
        """Test 2(1N,1A) - 2 repetitions of (digit or letter)."""
        regex = compile_pattern_to_regex("2(1N,1A)")
        assert re.fullmatch(regex, "1A")
        assert re.fullmatch(regex, "A1")
        assert re.fullmatch(regex, "12")
        assert re.fullmatch(regex, "AB")
        assert not re.fullmatch(regex, "1")
        assert not re.fullmatch(regex, "123")

    def test_nested_quantified_groups(self):
        """Test 2(3(1N)) - 2 repetitions of (3 repetitions of 1 digit)."""
        regex = compile_pattern_to_regex("2(3(1N))")
        assert re.fullmatch(regex, "123456")  # 2 groups of 3 digits
        assert not re.fullmatch(regex, "12345")  # Not enough
        assert not re.fullmatch(regex, "1234567")  # Too many

    def test_indefinite_quantified_group(self):
        """Test .(2N) - any number of groups of exactly 2 digits."""
        regex = compile_pattern_to_regex(".(2N)")
        assert re.fullmatch(regex, "")  # 0 groups
        assert re.fullmatch(regex, "12")  # 1 group
        assert re.fullmatch(regex, "1234")  # 2 groups
        assert not re.fullmatch(regex, "123")  # 1.5 groups


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
