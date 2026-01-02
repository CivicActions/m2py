"""Tests for USE command code generation (§8.2.23).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.23
"""

import pytest


@pytest.mark.codegen
class TestUseCommandCodegen:
    """Codegen-level tests for USE command code generation (§8.2.23)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: USE to device select")
    def test_use_to_device_select(self, generate_python):
        """USE generates device/file selection (§8.2.23)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: USE with parameters")
    def test_use_with_parameters(self, generate_python):
        """USE parameters translate to device options (§8.2.23)."""
        pytest.fail("Stub - implement test")
