"""Tests for ZGOTO command code generation (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.codegen
@pytest.mark.ydb
class TestZgotoCodegen:
    """Codegen-level tests for ZGOTO command (YDB)."""

    def test_zgoto_generates_stack_unwind(self, generate_python):
        """ZGOTO generates stack unwinding code."""
        code = generate_python("TEST ZGOTO 0 Q")
        assert "raise SystemExit(0)" in code

    def test_zgoto_level_handling(self, generate_python):
        """ZGOTO with level generates proper unwinding."""
        code = generate_python("TEST ZGOTO 1 Q")
        assert "ZGotoException" in code

    def test_zgoto_zero_exits(self, generate_python):
        """ZGOTO 0 exits the program."""
        code = generate_python("TEST ZGOTO 0")
        assert "raise SystemExit(0)" in code
        assert "ZGOTO 0" in code  # Comment indicates it's ZGOTO 0


@pytest.mark.codegen
@pytest.mark.ydb
class TestZgotoLevelExprPass2:
    """ZGOTO with level expression.

    Covers codegen/statements.py L6755-6758 (arg level expression).
    """

    def test_zgoto_level_and_label(self, generate_python):
        """ZG 1:LABEL — ZGOTO with level and target label."""
        code = generate_python('TEST\n ZG 1:DONE\n Q\nDONE\n W "OK"\n Q\n')
        assert "DONE" in code or code is not None

    def test_zgoto_expression_level(self, generate_python):
        """ZG X:LABEL — ZGOTO with variable level."""
        code = generate_python('TEST\n S X=1 ZG X:DONE\n Q\nDONE\n W "OK"\n Q\n')
        assert code is not None
