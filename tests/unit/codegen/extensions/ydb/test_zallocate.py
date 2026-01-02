"""Tests for ZALLOCATE/ZDEALLOCATE command code generation (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.codegen
@pytest.mark.ydb
class TestZallocateCodegen:
    """Codegen-level tests for ZALLOCATE/ZDEALLOCATE command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZALLOCATE codegen")
    def test_zallocate_generates_lock(self, generate_python):
        """ZALLOCATE generates incremental lock."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZDEALLOCATE codegen")
    def test_zdeallocate_generates_unlock(self, generate_python):
        """ZDEALLOCATE generates lock release."""
        pytest.fail("Stub - implement test")
