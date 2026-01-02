"""Tests for ZSYSTEM command code generation (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.codegen
@pytest.mark.ydb
class TestZsystemCodegen:
    """Codegen-level tests for ZSYSTEM command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZSYSTEM codegen")
    def test_zsystem_generates_subprocess(self, generate_python):
        """ZSYSTEM generates subprocess call."""
        pytest.fail("Stub - implement test")
