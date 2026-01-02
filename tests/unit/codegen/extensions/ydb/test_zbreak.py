"""Tests for ZBREAK command code generation (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.codegen
@pytest.mark.ydb
class TestZbreakCodegen:
    """Codegen-level tests for ZBREAK command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZBREAK codegen")
    def test_zbreak_generates_breakpoint(self, generate_python):
        """ZBREAK generates debugger breakpoint."""
        pytest.fail("Stub - implement test")
