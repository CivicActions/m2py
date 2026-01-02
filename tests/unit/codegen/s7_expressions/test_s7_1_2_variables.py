"""Tests for Variables code generation (§7.1.2).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.2
"""

import pytest


@pytest.mark.codegen
class TestVariablesCodegen:
    """Codegen-level tests for variables code generation (§7.1.2)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: local variable access")
    def test_local_variable_access(self, generate_python):
        """Local variable access generates dict lookup (§7.1.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: global variable access")
    def test_global_variable_access(self, generate_python):
        """Global variable access generates globals dict lookup (§7.1.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: subscripted access")
    def test_subscripted_access(self, generate_python):
        """Subscripted variable access generates nested lookup (§7.1.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: naked global")
    def test_naked_global(self, generate_python):
        """Naked global reference uses stored reference (§7.1.2)."""
        pytest.fail("Stub - implement test")
