"""Tests for §8 ksubscripts code generation.

Reference: MUMPS 1995 ANSI Standard, Section 8.2.20 (shared numbering)
"""

import pytest


@pytest.mark.codegen
class TestKsubscriptsCodegen:
    """Codegen-level tests for ksubscripts code generation."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ksubscripts codegen")
    def test_ksubscripts_codegen(self, generate_python):
        """Ksubscripts generates correct subscript access."""
        pytest.fail("Stub - implement test")
