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
