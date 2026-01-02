"""Tests for RSAVE command code generation (§8.2.29).

Out of scope per FR-055.
Reference: MUMPS 1995 ANSI Standard, Section 8.2.29
"""

import pytest


@pytest.mark.codegen
@pytest.mark.skip(reason="Out of scope: RSAVE command per FR-055")
class TestRsaveCommandCodegen:
    """RSAVE command is out of scope (FR-055)."""

    def test_rsave_codegen(self, generate_python):
        """RSAVE command not in scope."""
        pass
