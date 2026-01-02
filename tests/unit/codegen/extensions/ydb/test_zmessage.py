"""Tests for ZMESSAGE command code generation (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.codegen
@pytest.mark.ydb
class TestZmessageCodegen:
    """Codegen-level tests for ZMESSAGE command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZMESSAGE codegen")
    def test_zmessage_generates_error_signal(self, generate_python):
        """ZMESSAGE generates error/message signal."""
        pytest.fail("Stub - implement test")
