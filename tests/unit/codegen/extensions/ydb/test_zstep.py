"""Tests for ZSTEP command code generation (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.codegen
@pytest.mark.ydb
class TestZstepCodegen:
    """Codegen-level tests for ZSTEP command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZSTEP codegen")
    def test_zstep_generates_debug_step(self, generate_python):
        """ZSTEP generates debug stepping."""
        pytest.fail("Stub - implement test")
