"""Tests for TROLLBACK command code generation (§8.2.21).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.21
"""

import pytest


@pytest.mark.codegen
class TestTrollbackCommandCodegen:
    """Codegen-level tests for TROLLBACK command code generation (§8.2.21)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: TROLLBACK to rollback")
    def test_trollback_to_rollback(self, generate_python):
        """TROLLBACK generates transaction rollback (§8.2.21)."""
        pytest.fail("Stub - implement test")
