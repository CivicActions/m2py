"""Tests for RLOAD command code generation (§8.2.28).

Out of scope per FR-055.
Reference: MUMPS 1995 ANSI Standard, Section 8.2.28
"""

import pytest


@pytest.mark.codegen
@pytest.mark.skip(reason="Out of scope: RLOAD command per FR-055")
class TestRloadCommandCodegen:
    """RLOAD command is out of scope (FR-055)."""

    def test_rload_codegen(self, generate_python):
        """RLOAD command not in scope."""
        pass
