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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: IF multiple conditions")
    def test_if_multiple_conditions(self, generate_python):
        """IF with comma-separated conditions generates AND (§8.2.9)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: IF argumentless")
    def test_if_argumentless(self, generate_python):
        """IF argumentless uses $TEST (§8.2.9)."""
        pytest.fail("Stub - implement test")
