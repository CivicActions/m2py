"""Tests for ZLINK command code generation (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.codegen
@pytest.mark.ydb
class TestZlinkCodegen:
    """Codegen-level tests for ZLINK command (YDB)."""

    def test_zlink_generates_import(self, generate_python):
        """ZLINK generates runtime zlink call."""
        code = generate_python('TEST ZLINK "MYMOD" Q')
        assert "_rt.zlink(" in code
        assert '"MYMOD"' in code or "'MYMOD'" in code

    def test_zlink_with_variable(self, generate_python):
        """ZLINK with variable generates dynamic import."""
        code = generate_python('TEST S X="MOD" ZLINK X Q')
        assert "_rt.zlink(" in code
