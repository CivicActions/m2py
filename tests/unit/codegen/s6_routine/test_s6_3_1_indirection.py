"""Tests for Indirection code generation (§6.3.1).

Reference: MUMPS 1995 ANSI Standard, Section 6.3.1
"""

import pytest


@pytest.mark.codegen
class TestIndirectionCodegen:
    """Codegen-level tests for indirection code generation (§6.3.1)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: name indirection")
    def test_name_indirection(self, generate_python):
        """Name indirection generates runtime evaluation (§6.3.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: subscript indirection")
    def test_subscript_indirection(self, generate_python):
        """Subscript indirection generates runtime evaluation (§6.3.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: argument indirection")
    def test_argument_indirection(self, generate_python):
        """Argument indirection generates runtime evaluation (§6.3.1)."""
        pytest.fail("Stub - implement test")
