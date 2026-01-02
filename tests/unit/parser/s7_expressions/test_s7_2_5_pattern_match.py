"""Tests for Pattern Match parsing (§7.2.5).

Tests verify the textX grammar correctly captures pattern match syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.2.5
Migrated from:
- tests/unit/test_grammar.py::TestPatternMatchGrammar
- tests/unit/test_grammar.py::TestIndirectPatternMatchGrammar
- tests/unit/test_special_constructs.py::TestPatternMatch
- tests/unit/test_pattern_compiler.py (pattern compiler tests)
"""

import re

import pytest

from m2py.asg import MRoutine
from m2py.parser import MUMPSParser
from m2py.analysis.pattern_compiler import (
    compile_pattern_to_regex,
    PatternCompileError,
)


@pytest.mark.parser
class TestPatternMatchParsing:
    """Parser-level tests for Pattern Match (§7.2.5).

    Pattern matching uses the ? operator with pattern atoms.

    Migrated from: tests/unit/test_special_constructs.py::TestPatternMatch
    """

    def test_pattern_operator_in_expr(self, parse_expression):
        """Pattern match operator ? is recognized with proper pattern syntax (§7.2.5).

        Migrated from: tests/unit/test_special_constructs.py::TestPatternMatch
        """
        model = parse_expression("X?1N")
        assert model is not None

    def test_negated_pattern(self, parse_expression):
        """Negated pattern '? (§7.2.5).

        Migrated from: tests/unit/test_special_constructs.py::TestPatternMatch
        """
        model = parse_expression("X'?1A")
        assert model is not None


@pytest.mark.parser
class TestPatternMatchGrammar:
    """Test pattern match expression parsing full-routine acceptance (§7.2.5).

    Migrated from: tests/unit/test_grammar.py::TestPatternMatchGrammar
    """

    def test_pattern_match_simple(self):
        """Pattern match X?1A.N should parse (§7.2.5)."""
        parser = MUMPSParser()
        source = 'LABEL\tI X?1A.N W "match"\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        assert len(routine.labels) == 1

    def test_pattern_match_negated(self):
        """Negated pattern match X'?1N should parse (§7.2.5)."""
        parser = MUMPSParser()
        source = 'LABEL\tI X\'?1N W "not numeric"\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_pattern_match_complex(self):
        """Complex pattern X?1A.ANP should parse (§7.2.5)."""
        parser = MUMPSParser()
        source = 'LABEL\tI NAME?1U.L W "valid"\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_pattern_match_numeric_repcount_exact(self):
        """Pattern with exact repcount X?2N should parse (T576 fix) (§7.2.5)."""
        parser = MUMPSParser()
        source = "LABEL\tS X=Y?2N\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_pattern_match_numeric_repcount_atleast(self):
        """Pattern with at-least repcount X?2.N should parse (T576 fix) (§7.2.5)."""
        parser = MUMPSParser()
        source = "LABEL\tS X=Y?2.N\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_pattern_match_numeric_repcount_atmost(self):
        """Pattern with at-most repcount X?.2N should parse (T576 fix) (§7.2.5)."""
        parser = MUMPSParser()
        source = "LABEL\tS X=Y?.2N\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_pattern_match_numeric_repcount_range(self):
        """Pattern with range repcount X?1.2N should parse (T576 fix) (§7.2.5)."""
        parser = MUMPSParser()
        source = "LABEL\tS X=Y?1.2N\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_pattern_match_multi_atom_with_repcounts(self):
        """Multi-atom pattern X?2.N.P.2N should parse (T576 fix) (§7.2.5)."""
        parser = MUMPSParser()
        source = "LABEL\tS X=Y?2.N.P.2N\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestIndirectPatternMatchGrammar:
    """Test indirect pattern match expression parsing (§7.2.5).

    Migrated from: tests/unit/test_grammar.py::TestIndirectPatternMatchGrammar
    """

    def test_indirect_pattern_match_simple(self):
        """Indirect pattern match X?@PAT should parse (§7.2.5)."""
        parser = MUMPSParser()
        source = "LABEL\tS X=Y?@PAT\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_indirect_pattern_match_with_parens(self):
        """Indirect pattern match X?@(PAT) should parse (§7.2.5)."""
        parser = MUMPSParser()
        source = "LABEL\tS X=Y?@(PAT)\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_indirect_pattern_match_string_literal(self):
        """Indirect pattern match with string literal should parse (§7.2.5)."""
        parser = MUMPSParser()
        source = 'LABEL\tS X="ABC"?@".4AN"\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_indirect_pattern_with_concat(self):
        """Indirect pattern followed by concatenation should parse (VV2PAT2 line 155) (§7.2.5)."""
        parser = MUMPSParser()
        source = 'LABEL\tS X="ABC"?@".4AN"_("12.34"?2.N.P.2N)\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


# =============================================================================
# Pattern Compiler Tests
# =============================================================================
# Migrated from: tests/unit/test_pattern_compiler.py


@pytest.mark.parser
class TestBasicPatternCodes:
    """Test individual pattern codes (§7.2.5).

    Migrated from: tests/unit/test_pattern_compiler.py::TestBasicPatternCodes
    """

    def test_single_alpha(self):
        """Test single alphabetic character (§7.2.5)."""
        regex = compile_pattern_to_regex("1A")
        assert re.fullmatch(regex, "A")
        assert re.fullmatch(regex, "z")
        assert not re.fullmatch(regex, "1")
        assert not re.fullmatch(regex, " ")

    def test_single_numeric(self):
        """Test single numeric character (§7.2.5)."""
        regex = compile_pattern_to_regex("1N")
        assert re.fullmatch(regex, "5")
        assert re.fullmatch(regex, "0")
        assert not re.fullmatch(regex, "A")
        assert not re.fullmatch(regex, "-")

    def test_single_lowercase(self):
        """Test single lowercase alphabetic (§7.2.5)."""
        regex = compile_pattern_to_regex("1L")
        assert re.fullmatch(regex, "a")
        assert re.fullmatch(regex, "z")
        assert not re.fullmatch(regex, "A")
        assert not re.fullmatch(regex, "5")

    def test_single_uppercase(self):
        """Test single uppercase alphabetic (§7.2.5)."""
        regex = compile_pattern_to_regex("1U")
        assert re.fullmatch(regex, "A")
        assert re.fullmatch(regex, "Z")
        assert not re.fullmatch(regex, "a")
        assert not re.fullmatch(regex, "5")

    def test_single_everything(self):
        """Test single everything character (§7.2.5)."""
        regex = compile_pattern_to_regex("1E")
        assert re.fullmatch(regex, "A")
        assert re.fullmatch(regex, "5")
        assert re.fullmatch(regex, " ")
        assert re.fullmatch(regex, "#")

    def test_single_punctuation(self):
        """Test single punctuation character (§7.2.5)."""
        regex = compile_pattern_to_regex("1P")
        assert re.fullmatch(regex, " ")
        assert re.fullmatch(regex, "!")
        assert re.fullmatch(regex, "-")
        assert not re.fullmatch(regex, "A")
        assert not re.fullmatch(regex, "5")

    def test_single_control(self):
        """Test single control character (§7.2.5)."""
        regex = compile_pattern_to_regex("1C")
        assert re.fullmatch(regex, "\t")
        assert re.fullmatch(regex, "\n")
        assert re.fullmatch(regex, "\x00")
        assert not re.fullmatch(regex, "A")


@pytest.mark.parser
class TestRepeatCounts:
    """Test repeat count variations (§7.2.5).

    Migrated from: tests/unit/test_pattern_compiler.py::TestRepeatCounts
    """

    def test_exact_count(self):
        """Test exact count (3N = exactly 3 digits) (§7.2.5)."""
        regex = compile_pattern_to_regex("3N")
        assert re.fullmatch(regex, "123")
        assert re.fullmatch(regex, "000")
        assert not re.fullmatch(regex, "12")
        assert not re.fullmatch(regex, "1234")

    def test_zero_count(self):
        """Test zero count (0N = empty string) (§7.2.5)."""
        regex = compile_pattern_to_regex("0N")
        assert re.fullmatch(regex, "")
        assert not re.fullmatch(regex, "1")

    def test_any_count(self):
        """Test indefinite multiplier (.N = any number) (§7.2.5)."""
        regex = compile_pattern_to_regex(".N")
        assert re.fullmatch(regex, "")
        assert re.fullmatch(regex, "1")
        assert re.fullmatch(regex, "12345")

    def test_at_least(self):
        """Test at least n (2. = 2 or more) (§7.2.5)."""
        regex = compile_pattern_to_regex("2.N")
        assert not re.fullmatch(regex, "")
        assert not re.fullmatch(regex, "1")
        assert re.fullmatch(regex, "12")
        assert re.fullmatch(regex, "12345")

    def test_at_most(self):
        """Test at most n (.2N = 0 to 2) (§7.2.5)."""
        regex = compile_pattern_to_regex(".2N")
        assert re.fullmatch(regex, "")
        assert re.fullmatch(regex, "1")
        assert re.fullmatch(regex, "12")
        assert not re.fullmatch(regex, "123")

    def test_range(self):
        """Test range (2.4N = 2 to 4) (§7.2.5)."""
        regex = compile_pattern_to_regex("2.4N")
        assert not re.fullmatch(regex, "1")
        assert re.fullmatch(regex, "12")
        assert re.fullmatch(regex, "123")
        assert re.fullmatch(regex, "1234")
        assert not re.fullmatch(regex, "12345")


@pytest.mark.parser
class TestConcatenatedPatterns:
    """Test concatenated pattern atoms (§7.2.5).

    Migrated from: tests/unit/test_pattern_compiler.py::TestConcatenatedPatterns
    """

    def test_letter_then_numbers(self):
        """Test 1A.N (one letter followed by any digits) (§7.2.5)."""
        regex = compile_pattern_to_regex("1A.N")
        assert re.fullmatch(regex, "A")
        assert re.fullmatch(regex, "A1")
        assert re.fullmatch(regex, "Z123")
        assert not re.fullmatch(regex, "1A")
        assert not re.fullmatch(regex, "")

    def test_phone_number_format(self):
        """Test phone number pattern (3N1\"-\"4N) (§7.2.5)."""
        regex = compile_pattern_to_regex('3N"-"4N')
        assert re.fullmatch(regex, "123-4567")
        assert not re.fullmatch(regex, "12-4567")
        assert not re.fullmatch(regex, "123-456")


@pytest.mark.parser
class TestStringLiterals:
    """Test string literal patterns (§7.2.5).

    Migrated from: tests/unit/test_pattern_compiler.py::TestStringLiterals
    """

    def test_simple_literal(self):
        """Test simple string literal (§7.2.5)."""
        regex = compile_pattern_to_regex('1"hello"')
        assert re.fullmatch(regex, "hello")
        assert not re.fullmatch(regex, "HELLO")

    def test_literal_with_special_chars(self):
        """Test literal with regex special characters (§7.2.5)."""
        regex = compile_pattern_to_regex('1"a.b*c"')
        assert re.fullmatch(regex, "a.b*c")
        assert not re.fullmatch(regex, "aXbXc")

    def test_escaped_quote(self):
        """Test escaped quote in literal (§7.2.5)."""
        regex = compile_pattern_to_regex('1"say ""hello"""')
        assert re.fullmatch(regex, 'say "hello"')


@pytest.mark.parser
class TestAlternation:
    """Test alternation patterns (§7.2.5).

    Migrated from: tests/unit/test_pattern_compiler.py::TestAlternation
    """

    def test_simple_alternation(self):
        """Test simple alternation (1N,1A) - either digit or letter (§7.2.5)."""
        regex = compile_pattern_to_regex("1(1N,1A)")
        assert re.fullmatch(regex, "5")
        assert re.fullmatch(regex, "A")
        assert not re.fullmatch(regex, " ")


@pytest.mark.parser
class TestRealWorldPatterns:
    """Test patterns from real MUMPS code (§7.2.5).

    Migrated from: tests/unit/test_pattern_compiler.py::TestRealWorldPatterns
    """

    def test_identifier_pattern(self):
        """Test MUMPS identifier pattern (1A.AN) (§7.2.5)."""
        regex = compile_pattern_to_regex("1A.AN")
        assert re.fullmatch(regex, "X")
        assert re.fullmatch(regex, "VAR1")
        assert re.fullmatch(regex, "Test123")
        assert not re.fullmatch(regex, "1VAR")
        assert not re.fullmatch(regex, "")

    def test_numeric_literal_pattern(self):
        """Test numeric with optional decimal (.N.1\".\".N) (§7.2.5)."""
        regex = compile_pattern_to_regex('.N.1".".N')
        assert re.fullmatch(regex, "123")
        assert re.fullmatch(regex, "123.45")
        assert re.fullmatch(regex, ".5")
        assert re.fullmatch(regex, "")

    def test_any_string(self):
        """Test any string pattern (.E) (§7.2.5)."""
        regex = compile_pattern_to_regex(".E")
        assert re.fullmatch(regex, "")
        assert re.fullmatch(regex, "anything goes here 123!@#")


@pytest.mark.parser
class TestCaseInsensitivity:
    """Test that pattern codes are case-insensitive (§7.2.5).

    Migrated from: tests/unit/test_pattern_compiler.py::TestCaseInsensitivity
    """

    def test_lowercase_patcode(self):
        """Test lowercase pattern codes work same as uppercase (§7.2.5)."""
        regex_upper = compile_pattern_to_regex("1A")
        regex_lower = compile_pattern_to_regex("1a")
        assert re.fullmatch(regex_upper, "X")
        assert re.fullmatch(regex_lower, "X")


@pytest.mark.parser
class TestEdgeCases:
    """Test edge cases and error handling (§7.2.5).

    Migrated from: tests/unit/test_pattern_compiler.py::TestEdgeCases
    """

    def test_empty_pattern(self):
        """Test empty pattern returns empty regex (§7.2.5)."""
        assert compile_pattern_to_regex("") == ""

    def test_unterminated_string(self):
        """Test unterminated string literal raises error (§7.2.5)."""
        with pytest.raises(PatternCompileError):
            compile_pattern_to_regex('1"hello')

    def test_invalid_patcode(self):
        """Test invalid pattern code raises error (§7.2.5)."""
        with pytest.raises(PatternCompileError):
            compile_pattern_to_regex("1X")


@pytest.mark.parser
class TestPatternMatchASGIntegration:
    """Test MPatternMatch.compiled_regex field behavior in ASG (§7.2.5).

    Migrated from: tests/unit/test_pattern_compiler.py::TestPatternMatchASGIntegration
    """

    def test_compiled_regex_populated_for_simple_pattern(self):
        """Pattern match with simple pattern should have compiled_regex populated (§7.2.5)."""
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
        """Indirect pattern (?@VAR) should have compiled_regex=None (§7.2.5).

        Indirect patterns cannot be pre-compiled because the pattern value
        is determined at runtime. The semantic analyzer gracefully leaves
        compiled_regex as None in these cases.
        """
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
