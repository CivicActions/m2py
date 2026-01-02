"""Tests for ZGOTO command code generation (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.codegen
@pytest.mark.ydb
class TestZgotoCodegen:
    """Codegen-level tests for ZGOTO command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZGOTO codegen")
    def test_zgoto_generates_stack_unwind(self, generate_python):
        """ZGOTO generates stack unwinding code."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZGOTO level handling")
    def test_zgoto_level_handling(self, generate_python):
        """ZGOTO with level generates proper unwinding."""
        pytest.fail("Stub - implement test")
