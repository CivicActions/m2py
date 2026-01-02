"""Tests for GOTO command code generation (§8.2.6).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.6
"""

import pytest


@pytest.mark.codegen
class TestGotoCommandCodegen:
    """Codegen-level tests for GOTO command code generation (§8.2.6)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: GOTO to function call")
    def test_goto_to_function_call(self, generate_python):
        """Simple GOTO generates function call with return (§8.2.6)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: GOTO computed")
    def test_goto_computed(self, generate_python):
        """Computed GOTO generates dispatch table (§8.2.6)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: GOTO external")
    def test_goto_external(self, generate_python):
        """External GOTO generates import and call (§8.2.6)."""
        pytest.fail("Stub - implement test")
