"""Tests for DO command code generation (§8.2.3).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.3
"""

import pytest


@pytest.mark.codegen
class TestDoCommandCodegen:
    """Codegen-level tests for DO command code generation (§8.2.3)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO call codegen")
    def test_do_call_codegen(self, generate_python):
        """DO generates function call (§8.2.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO with args")
    def test_do_with_args(self, generate_python):
        """DO with arguments generates parameterized call (§8.2.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO block codegen")
    def test_do_block_codegen(self, generate_python):
        """DO block generates indented block (§8.2.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO external routine")
    def test_do_external_routine(self, generate_python):
        """DO external routine generates import and call (§8.2.3)."""
        pytest.fail("Stub - implement test")
