"""Tests for CLOSE command code generation (§8.2.2).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.2
"""

import pytest


@pytest.mark.codegen
class TestCloseCommandCodegen:
    """Codegen-level tests for CLOSE command code generation (§8.2.2)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: CLOSE codegen")
    def test_close_codegen(self, generate_python):
        """CLOSE generates file/device close (§8.2.2)."""
        pytest.fail("Stub - implement test")
