"""Tests for ZKILL/ZWITHDRAW command code generation (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.codegen
@pytest.mark.ydb
class TestZkillCodegen:
    """Codegen-level tests for ZKILL/ZWITHDRAW command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZKILL codegen")
    def test_zkill_generates_node_delete(self, generate_python):
        """ZKILL generates node-only delete (keeps descendants)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZWITHDRAW codegen")
    def test_zwithdraw_generates_node_delete(self, generate_python):
        """ZWITHDRAW generates node-only delete (keeps descendants)."""
        pytest.fail("Stub - implement test")
