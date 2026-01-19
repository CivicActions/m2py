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
