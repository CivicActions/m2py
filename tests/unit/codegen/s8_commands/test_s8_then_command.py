"""Tests for THEN command code generation (§8.2.32).

Out of scope per FR-055.
Reference: MUMPS 1995 ANSI Standard, Section 8.2.32
"""

import pytest


@pytest.mark.codegen
@pytest.mark.skip(
    reason="Out of scope: THEN command per FR-055 (zero real-world usage)"
)
class TestThenCommandCodegen:
    """THEN command is out of scope (FR-055)."""

    def test_then_codegen(self, generate_python):
        """THEN command not in scope."""
        pass
