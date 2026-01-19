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
