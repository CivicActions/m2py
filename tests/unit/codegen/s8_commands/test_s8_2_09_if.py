"""Tests for IF command code generation (§8.2.9).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.9
"""

import pytest


@pytest.mark.codegen
class TestIfCommandCodegen:
    """Codegen-level tests for IF command code generation (§8.2.9)."""

    def test_if_to_if_statement(self, generate_python):
        """IF generates Python if statement (§8.2.9)."""
        code = generate_python('TEST\n I 1 W "YES"\n Q\n')
        assert "if _test:" in code or "if m_truth" in code

    def test_if_test_update(self, generate_python):
        """IF updates $TEST after evaluation (§8.2.9)."""
        code = generate_python('TEST\n I 1>0 W "YES"\n Q\n')
        assert "_test = m_truth(" in code

    def test_if_true_branch(self, execute_mumps):
        """IF executes body when condition is true.

        User Story 2 acceptance scenario 1:
        Given: S X=5 I X>3 W "GT" E W "LE"
        When: generated and executed
        Then: output is "GT"
        """
        result = execute_mumps('TEST\n S X=5\n I X>3 W "GT"\n E W "LE"\n Q\n')
        assert result.output == "GT"
        assert result.success is True

    def test_if_false_branch(self, execute_mumps):
        """IF skips body when condition is false.

        User Story 2 acceptance scenario 2:
        Given: S X=1 I X>3 W "GT" E W "LE"
        When: generated and executed
        Then: output is "LE"
        """
        result = execute_mumps('TEST\n S X=1\n I X>3 W "GT"\n E W "LE"\n Q\n')
        assert result.output == "LE"
        assert result.success is True

    def test_if_zero_is_false(self, execute_mumps):
        """Zero evaluates to false in IF condition.

        User Story 2 acceptance scenario 3:
        Given: S X=0 I X W "TRUE" E W "FALSE"
        When: generated and executed
        Then: output is "FALSE" (zero is false)
        """
        result = execute_mumps('TEST\n S X=0\n I X W "TRUE"\n E W "FALSE"\n Q\n')
        assert result.output == "FALSE"
        assert result.success is True

    def test_if_string_zero_is_false(self, execute_mumps):
        """String "0" coerces to 0 → false in IF condition.

        User Story 6 acceptance scenario (T045):
        Given: I "0" W "TRUE" E W "FALSE"
        When: generated and executed
        Then: output is "FALSE" (string "0" coerces to 0, which is false)
        """
        result = execute_mumps('TEST\n I "0" W "TRUE"\n E W "FALSE"\n Q\n')
        assert result.output == "FALSE"
        assert result.success is True

    def test_if_string_with_leading_one_is_true(self, execute_mumps):
        """String "1A" coerces to 1 → true in IF condition.

        User Story 6 acceptance scenario (T046):
        Given: I "1A" W "TRUE" E W "FALSE"
        When: generated and executed
        Then: output is "TRUE" (string "1A" coerces to 1, which is true)
        """
        result = execute_mumps('TEST\n I "1A" W "TRUE"\n E W "FALSE"\n Q\n')
        assert result.output == "TRUE"
        assert result.success is True

    def test_if_string_with_no_leading_number_is_false(self, execute_mumps):
        """String "A" coerces to 0 → false in IF condition.

        User Story 6 acceptance scenario (T047):
        Given: I "A" W "TRUE" E W "FALSE"
        When: generated and executed
        Then: output is "FALSE" (string "A" coerces to 0, which is false)
        """
        result = execute_mumps('TEST\n I "A" W "TRUE"\n E W "FALSE"\n Q\n')
        assert result.output == "FALSE"
        assert result.success is True

    def test_if_string_coercion_in_comparison(self, execute_mumps):
        """String "3A" coerces to 3 in < comparison.

        User Story 6 acceptance scenario (T048):
        Given: I "3A"<5 W "YES" E W "NO"
        When: generated and executed
        Then: output is "YES" (string "3A" coerces to 3, and 3<5 is true)
        """
        result = execute_mumps('TEST\n I "3A"<5 W "YES"\n E W "NO"\n Q\n')
        assert result.output == "YES"
        assert result.success is True

    def test_if_multiple_conditions(self, execute_mumps):
        """IF with comma-separated conditions (AND) (§8.2.9).

        YDB verified: S X=3 I X>0,X<5 W "OK" → "OK"
        """
        result = execute_mumps('TEST\n S X=3\n I X>0,X<5 W "OK"\n Q\n')
        assert result.output == "OK"
        assert result.success is True

    def test_if_argumentless(self, execute_mumps):
        """IF argumentless uses $TEST (§8.2.9).

        YDB verified: I 1 I  W "YES" → "YES"
        """
        result = execute_mumps('TEST\n I 1 I  W "YES"\n Q\n')
        assert result.output == "YES"
        assert result.success is True
