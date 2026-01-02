"""Tests for ASSIGN command code generation.

Out of scope per FR-055.
Reference: MUMPS 1995 ANSI Standard
"""

import pytest


@pytest.mark.codegen
@pytest.mark.skip(reason="Out of scope: ASSIGN command per FR-055")
class TestAssignCommandCodegen:
    """ASSIGN command is out of scope (FR-055)."""

    def test_assign_codegen(self, generate_python):
        """ASSIGN command not in scope."""
        pass
