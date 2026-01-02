"""Tests for BREAK command code generation (§8.2.1).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.1
"""

import pytest


@pytest.mark.codegen
class TestBreakCommandCodegen:
    """Codegen-level tests for BREAK command code generation (§8.2.1)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: BREAK codegen")
    def test_break_codegen(self, generate_python):
        """BREAK generates debugger interaction (§8.2.1)."""
        pytest.fail("Stub - implement test")
