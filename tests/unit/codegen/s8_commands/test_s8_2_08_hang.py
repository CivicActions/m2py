"""Tests for HANG command code generation (§8.2.8).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.8
"""

import pytest


@pytest.mark.codegen
class TestHangCommandCodegen:
    """Codegen-level tests for HANG command code generation (§8.2.8)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: HANG to time.sleep")
    def test_hang_to_time_sleep(self, generate_python):
        """HANG generates time.sleep() (§8.2.8)."""
        pytest.fail("Stub - implement test")
