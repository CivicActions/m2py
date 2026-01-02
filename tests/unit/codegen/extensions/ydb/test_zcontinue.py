"""Tests for ZCONTINUE command code generation (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.codegen
@pytest.mark.ydb
class TestZcontinueCodegen:
    """Codegen-level tests for ZCONTINUE command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZCONTINUE codegen")
    def test_zcontinue_generates_resume(self, generate_python):
        """ZCONTINUE generates debug resume."""
        pytest.fail("Stub - implement test")
