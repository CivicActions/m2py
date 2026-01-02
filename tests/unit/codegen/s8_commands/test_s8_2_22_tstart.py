"""Tests for TSTART command code generation (§8.2.22).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.22
"""

import pytest


@pytest.mark.codegen
class TestTstartCommandCodegen:
    """Codegen-level tests for TSTART command code generation (§8.2.22)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: TSTART to begin")
    def test_tstart_to_begin(self, generate_python):
        """TSTART generates transaction begin (§8.2.22)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: TSTART serial")
    def test_tstart_serial(self, generate_python):
        """TSTART:SERIAL generates serializable transaction (§8.2.22)."""
        pytest.fail("Stub - implement test")
