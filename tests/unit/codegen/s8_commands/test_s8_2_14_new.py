"""Tests for NEW command code generation (§8.2.14).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.14
"""

import pytest


@pytest.mark.codegen
class TestNewCommandCodegen:
    """Codegen-level tests for NEW command code generation (§8.2.14)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW to scope push")
    def test_new_to_scope_push(self, generate_python):
        """NEW generates scope push (§8.2.14)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW exclusive")
    def test_new_exclusive(self, generate_python):
        """NEW exclusive generates selective scope (§8.2.14)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW scope cleanup")
    def test_new_scope_cleanup(self, generate_python):
        """NEW scope cleanup on QUIT (§8.2.14)."""
        pytest.fail("Stub - implement test")
