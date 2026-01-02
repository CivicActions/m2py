"""Tests for ZCOMPILE command code generation (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.codegen
@pytest.mark.ydb
class TestZcompileCodegen:
    """Codegen-level tests for ZCOMPILE command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZCOMPILE codegen")
    def test_zcompile_generates_compile_call(self, generate_python):
        """ZCOMPILE generates compilation call."""
        pytest.fail("Stub - implement test")
