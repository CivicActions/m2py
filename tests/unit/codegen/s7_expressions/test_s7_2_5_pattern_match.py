"""Tests for Pattern Match code generation (§7.2.5).

Reference: MUMPS 1995 ANSI Standard, Section 7.2.5
"""

import pytest


@pytest.mark.codegen
class TestPatternMatchCodegen:
    """Codegen-level tests for pattern match code generation (§7.2.5)."""

    def test_pattern_match_letters(self, execute_mumps):
        """Pattern match with letter pattern (§7.2.5).

        User Story 6 acceptance scenario 1:
        YDB verified: "ABC"?1A.A → 1
        """
        result = execute_mumps('TEST\n W "ABC"?1A.A\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_pattern_match_failure(self, execute_mumps):
        """Pattern match fails when pattern doesn't match (§7.2.5).

        User Story 6 acceptance scenario 2:
        YDB verified: "A1B"?1A.A → 0 (contains digit, fails letter-only pattern)
        """
        result = execute_mumps('TEST\n W "A1B"?1A.A\n Q\n')
        assert result.output == "0"
        assert result.success is True

    def test_pattern_match_digits(self, execute_mumps):
        """Pattern match with numeric pattern (§7.2.5).

        User Story 6 acceptance scenario 3:
        YDB verified: "123"?1N.N → 1
        """
        result = execute_mumps('TEST\n W "123"?1N.N\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_pattern_match_mixed(self, execute_mumps):
        """Pattern match with mixed pattern (§7.2.5).

        User Story 6 acceptance scenario 4:
        YDB verified: "AB12"?2A2N → 1
        """
        result = execute_mumps('TEST\n W "AB12"?2A2N\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_pattern_match_negated(self, execute_mumps):
        """Negated pattern match returns inverse (§7.2.5).

        YDB verified: "ABC"'?1N.N → 1 (ABC doesn't match numeric pattern)
        """
        result = execute_mumps('TEST\n W "ABC"\'?1N.N\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_pattern_alternation(self, execute_mumps):
        """Pattern alternation generates regex alternation (§7.2.5).

        User Story 4 (VistA Features) acceptance scenario SC-017:
        YDB verified: "AB"?1(1A,1N)1(1A,1N) → 1 (matches)

        Pattern alternation allows matching one of several alternatives.
        """
        result = execute_mumps('TEST\n W "AB"?1(1A,1N)1(1A,1N)\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_pattern_alternation_numeric_option(self, execute_mumps):
        """Pattern alternation with numeric option (§7.2.5).

        YDB verified: "12"?1(1A,1N)1(1A,1N) → 1 (two digits match)
        """
        result = execute_mumps('TEST\n W "12"?1(1A,1N)1(1A,1N)\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_pattern_alternation_failure(self, execute_mumps):
        """Pattern alternation fails when no alternative matches (§7.2.5).

        YDB verified: "A.B"?1(1A,1N)1(1A,1N) → 0 (dot not in alternation)
        """
        result = execute_mumps('TEST\n W "A.B"?1(1A,1N)1(1A,1N)\n Q\n')
        assert result.output == "0"
        assert result.success is True

    def test_pattern_alternation_phone_number(self, execute_mumps):
        """Pattern alternation for phone number format (§7.2.5).

        YDB verified: "123-456-7890"?3N1(1"-",1".")3N1(1"-",1".")4N → 1
        """
        result = execute_mumps(
            'TEST\n W "123-456-7890"?3N1(1"-",1".")3N1(1"-",1".")4N\n Q\n'
        )
        assert result.output == "1"
        assert result.success is True

    def test_pattern_alternation_nested(self, execute_mumps):
        """Nested pattern alternation (§7.2.5).

        YDB verified: "a"?1(1(1l,1u),2N) → 1 (lowercase matches inner alt)
        """
        result = execute_mumps('TEST\n W "a"?1(1(1l,1u),2N)\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_pattern_alternation_nested_outer(self, execute_mumps):
        """Nested pattern alternation matching outer option (§7.2.5).

        YDB verified: "12"?1(1(1l,1u),2N) → 1 (two digits match outer 2N option)
        """
        result = execute_mumps('TEST\n W "12"?1(1(1l,1u),2N)\n Q\n')
        assert result.output == "1"
        assert result.success is True


@pytest.mark.codegen
class TestPatternMatchOptimization:
    """Tests for pre-compiled pattern match optimization (§7.2.5).

    Spec 015 Phase 3: Verifies codegen uses pre-compiled regex for direct
    patterns instead of calling m_pattern_match() at runtime.

    Direct patterns (X?1A.N) are pre-compiled during semantic analysis and
    stored in MPatternMatch.compiled_regex. Codegen then uses inline
    re.fullmatch() for better performance.

    Indirect patterns (X?@Y) still use m_pattern_match() runtime helper
    since the pattern is determined at runtime.
    """

    def test_direct_pattern_uses_inline_regex(self, generate_python):
        """Direct pattern (X?1A.N) uses inline re.fullmatch (§7.2.5).

        During semantic analysis, the pattern is compiled to regex and stored
        in MPatternMatch.compiled_regex. Codegen uses this to generate inline
        re.fullmatch() instead of calling m_pattern_match().
        """
        code = generate_python('TEST S X="ABC" W X?1A.N Q\n')
        # Should use inline re.fullmatch with pre-compiled regex
        assert "re.fullmatch(" in code
        # The compiled regex for 1A.N includes letter class
        assert "[A-Za-z]" in code or "A-Za-z" in code
        # The pattern match expression should NOT call m_pattern_match function
        # (it may still be in imports, but not used for the expression)
        assert "m_pattern_match(_scope" not in code
        assert "m_pattern_match(str(" not in code

    def test_indirect_pattern_uses_runtime_helper(self, generate_python):
        """Indirect pattern (X?@Y) uses m_pattern_match runtime helper (§7.2.5).

        Indirect patterns cannot be pre-compiled since the pattern string
        is determined at runtime. These use m_pattern_match() which calls
        compile_pattern_to_regex() at runtime.
        """
        code = generate_python('TEST S X="ABC",P="1A.N" W X?@P Q\n')
        # Indirect pattern must use m_pattern_match (compiles at runtime)
        assert "m_pattern_match" in code

    def test_negated_pattern_uses_inline_regex(self, generate_python):
        """Negated pattern (X'?3N) uses inline re.fullmatch with not (§7.2.5).

        Negated direct patterns also use pre-compiled regex with int(not ...)
        wrapper to invert the boolean result.
        """
        code = generate_python('TEST S X="ABC" W X\'?3N Q\n')
        # Should use inline re.fullmatch
        assert "re.fullmatch(" in code
        # Should wrap in int(not ...) for negation
        assert "int(not" in code

    def test_pattern_match_execution_direct(self, execute_mumps):
        """Direct pattern match executes correctly with pre-compiled regex (§7.2.5).

        Validates that the inline re.fullmatch() produces correct results.
        """
        result = execute_mumps('TEST S X="Test123" W X?1A.AN,! Q\n')
        assert result.success is True
        assert result.output == "1\n"

    def test_pattern_match_execution_indirect(self, execute_mumps):
        """Indirect pattern match executes correctly with runtime compilation (§7.2.5).

        Validates that m_pattern_match() runtime helper produces correct results.
        """
        result = execute_mumps('TEST S X="999",P="3N" W X?@P,! Q\n')
        assert result.success is True
        assert result.output == "1\n"

    def test_indirect_pattern_match_edge(self, execute_mumps):
        """Indirect pattern match with variables exercises walk_expressions (§7.2.5).

        T061: Indirect pattern match edge case
        Given: S P="3N" W "123"?@P
        When: executed
        Then: output is "1" - pattern "3N" compiled at runtime matches "123"

        Reference: Finding 46 from research.md
        This exercises variables.py walk_expressions for MPatternMatch
        with pattern_indirect set. The walk yields from pattern_indirect
        to track variable dependencies.
        """
        result = execute_mumps('TEST\n S P="3N" W "123"?@P,!\n Q\n')
        assert result.output == "1\n"
        assert result.success is True

    def test_indirect_pattern_match_non_matching(self, execute_mumps):
        """Indirect pattern match returns 0 for non-match (§7.2.5).

        T061 complement: When the indirect pattern doesn't match.
        """
        result = execute_mumps('TEST\n S P="1N" W "ABC"?@P,!\n Q\n')
        assert result.output == "0\n"
        assert result.success is True

    def test_pattern_single_alternation_edge(self, execute_mumps):
        """Pattern alternation with single element exercises alternation parsing (§7.2.5).

        T063: Single alternation pattern edge case
        Given: W "A"?1(1A,1N)
        When: executed
        Then: output is "1" - alternation (1A OR 1N) matches single letter

        Reference: Finding 44 from research.md
        Alternation patterns like (1A,1N) allow matching one of multiple options.
        This exercises pattern_compiler.py _parse_alternation edge cases.
        """
        result = execute_mumps('TEST\n W "A"?1(1A,1N),!\n Q\n')
        assert result.output == "1\n"
        assert result.success is True

    def test_pattern_single_alternation_numeric(self, execute_mumps):
        """Pattern alternation matches numeric alternative (§7.2.5).

        T063 complement: Same alternation with numeric input.
        """
        result = execute_mumps('TEST\n W "5"?1(1A,1N),!\n Q\n')
        assert result.output == "1\n"
        assert result.success is True

    def test_pattern_single_alternation_non_match(self, execute_mumps):
        """Pattern alternation returns 0 when no alternative matches (§7.2.5).

        T063 complement: When neither alternative matches.
        """
        result = execute_mumps('TEST\n W "!"?1(1A,1N),!\n Q\n')
        assert result.output == "0\n"
        assert result.success is True

    def test_pattern_quantifiers_dot_max_edge(self, execute_mumps):
        """Pattern quantifier .N (0 to N) exercises quantifier parsing (§7.2.5).

        T064: Pattern quantifier edge case - .5A means 0 to 5 letters
        Given: W "ABC"?.5A
        When: executed
        Then: output is "1" - 3 letters is within 0-5 range
        """
        result = execute_mumps('TEST\n W "ABC"?.5A,!\n Q\n')
        assert result.output == "1\n"
        assert result.success is True

    def test_pattern_quantifiers_dot_max_exceeds(self, execute_mumps):
        """Pattern quantifier .N fails when count exceeds max (§7.2.5).

        T064 complement: 6 letters exceeds .5A (0-5 limit).
        """
        result = execute_mumps('TEST\n W "ABCDEF"?.5A,!\n Q\n')
        assert result.output == "0\n"
        assert result.success is True

    def test_pattern_quantifiers_min_dot_edge(self, execute_mumps):
        """Pattern quantifier N. (N or more) exercises quantifier parsing (§7.2.5).

        T064: Pattern quantifier edge case - 3.N means 3 or more numbers
        Given: W "12345"?3.N
        When: executed
        Then: output is "1" - 5 numbers is at least 3
        """
        result = execute_mumps('TEST\n W "12345"?3.N,!\n Q\n')
        assert result.output == "1\n"
        assert result.success is True

    def test_pattern_quantifiers_min_dot_below_min(self, execute_mumps):
        """Pattern quantifier N. fails when count is below minimum (§7.2.5).

        T064 complement: 2 numbers is below 3.N (minimum 3) limit.
        """
        result = execute_mumps('TEST\n W "12"?3.N,!\n Q\n')
        assert result.output == "0\n"
        assert result.success is True

    def test_pattern_quantifiers_range_edge(self, execute_mumps):
        """Pattern quantifier M.N (M to N) exercises range quantifier (§7.2.5).

        T064: Pattern quantifier edge case - 3.5A means 3 to 5 letters
        Given: W "ABC"?3.5A
        When: executed
        Then: output is "1" - 3 letters is within 3-5 range
        """
        result = execute_mumps('TEST\n W "ABC"?3.5A,!\n Q\n')
        assert result.output == "1\n"
        assert result.success is True


@pytest.mark.codegen
class TestPatternMatchWithMStr:
    """Tests for pattern match using m_str (MUMPS canonical formatting).

    Fix: Changed pattern match from str() to m_str() so numeric values
    are formatted in MUMPS canonical form before pattern matching.
    """

    def test_pattern_match_leading_zero_removed(self, execute_mumps):
        """Pattern match on 0.5 uses ".5" not "0.5"."""
        # 0.5 in MUMPS is canonically ".5" so it matches ".5"?1P1N
        result = execute_mumps("TEST S X=0.5 W X?1P1N Q")
        assert result.success is True
        # ".5" matches 1P (period) 1N (digit) - should be true (1)
        assert result.output == "1"

    def test_pattern_match_negative_leading_zero(self, execute_mumps):
        """Pattern match on -0.5 uses "-.5" not "-0.5"."""
        result = execute_mumps('TEST S X=-0.5 W X?1"-"1P1N Q')
        assert result.success is True
        # "-.5" matches 1"-" 1P (period) 1N (digit) - should be true (1)
        assert result.output == "1"

    def test_pattern_match_integer_no_decimal(self, execute_mumps):
        """Pattern match on 1.0 uses "1" not "1.0"."""
        result = execute_mumps("TEST S X=1.0 W X?1N Q")
        assert result.success is True
        # "1" matches 1N - should be true (1)
        assert result.output == "1"


@pytest.mark.codegen
class TestPatternIndirection:
    """Tests for pattern match with indirection."""

    def test_pattern_match_indirection(self, execute_mumps):
        """X?@PAT — pattern match with indirected pattern."""
        result = execute_mumps('TEST\n\tS PAT="3N"\n\tW "123"?@PAT\n\tQ\n')
        assert result.output == "1"

    def test_pattern_match_indirection_no_match(self, execute_mumps):
        """X?@PAT — pattern doesn't match."""
        result = execute_mumps('TEST\n\tS PAT="3N"\n\tW "ABC"?@PAT\n\tQ\n')
        assert result.output == "0"
