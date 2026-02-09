"""Tests for ZHALT command code generation (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.codegen
@pytest.mark.ydb
class TestZhaltCodegen:
    """Codegen-level tests for ZHALT command (YDB)."""

    def test_zhalt_generates_exit(self, generate_python):
        """ZHALT generates sys.exit with status."""
        code = generate_python("TEST ZHALT 42")
        assert "raise SystemExit(int(42))" in code

    def test_zhalt_default_zero(self, generate_python):
        """ZHALT without argument defaults to 0."""
        code = generate_python("TEST ZHALT")
        assert "raise SystemExit(0)" in code

    def test_zhalt_with_expression(self, generate_python):
        """ZHALT accepts expressions."""
        code = generate_python("TEST S X=1 ZHALT X+1")
        assert "SystemExit" in code
        # Should generate expression evaluation
        assert "int(" in code


@pytest.mark.codegen
@pytest.mark.ydb
class TestZhaltExpressionPass2:
    """ZHALT with exit code expression.

    Covers codegen/statements.py L6791-6793.
    """

    def test_zhalt_numeric_literal(self, generate_python):
        """ZHALT 2 — halt with specific exit code."""
        code = generate_python("TEST\n ZHALT 2\n Q\n")
        assert "SystemExit" in code
        assert "2" in code

    def test_zhalt_complex_expression(self, generate_python):
        """ZHALT 1+2*3 — halt with computed exit code."""
        code = generate_python("TEST\n ZHALT 1+2*3\n Q\n")
        assert "SystemExit" in code
        assert "int(" in code
