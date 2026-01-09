"""Tests for ELSE command code generation (§8.2.4).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.4
"""

import pytest


@pytest.mark.codegen
class TestElseCommandCodegen:
    """Codegen-level tests for ELSE command code generation (§8.2.4)."""

    def test_else_codegen(self, generate_python):
        """ELSE generates if not _test clause (§8.2.4)."""
        code = generate_python('TEST\n I 0 W "YES"\n E W "NO"\n Q\n')
        assert "if not _test:" in code

    def test_else_test_usage(self, execute_mumps):
        """ELSE uses $TEST value (§8.2.4).

        ELSE executes when $TEST is false from previous IF.
        """
        result = execute_mumps('TEST\n I 0 W "YES"\n E W "NO"\n Q\n')
        assert result.output == "NO"
        assert result.success is True
