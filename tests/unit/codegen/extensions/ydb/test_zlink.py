"""Tests for ZLINK command code generation (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.codegen
@pytest.mark.ydb
class TestZlinkCodegen:
    """Codegen-level tests for ZLINK command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZLINK codegen")
    def test_zlink_generates_import(self, generate_python):
        """ZLINK generates import statement."""
        pytest.fail("Stub - implement test")
