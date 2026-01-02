"""Tests for ZHELP command code generation (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.codegen
@pytest.mark.ydb
class TestZhelpCodegen:
    """Codegen-level tests for ZHELP command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZHELP codegen")
    def test_zhelp_generates_help(self, generate_python):
        """ZHELP generates help lookup."""
        pytest.fail("Stub - implement test")
