"""Tests for §8 kvalue code generation.

Reference: MUMPS 1995 ANSI Standard, Section 8.2.21 (shared numbering)
"""

import pytest


@pytest.mark.codegen
class TestKvalueCodegen:
    """Codegen-level tests for kvalue code generation."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: kvalue codegen")
    def test_kvalue_codegen(self, generate_python):
        """Kvalue generates correct value access."""
        pytest.fail("Stub - implement test")
