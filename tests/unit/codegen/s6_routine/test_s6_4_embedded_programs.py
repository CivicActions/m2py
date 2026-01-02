"""Tests for Embedded Programs code generation (§6.4).

Reference: MUMPS 1995 ANSI Standard, Section 6.4
"""

import pytest


@pytest.mark.codegen
class TestEmbeddedProgramsCodegen:
    """Codegen-level tests for embedded programs code generation (§6.4)."""

    @pytest.mark.skip(reason="Out of scope: Embedded programs (§6.4) per FR-055")
    def test_embedded_programs(self):
        """Embedded programs are out of scope (§6.4)."""
        pass
