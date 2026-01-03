"""Tests for ASSIGN command parsing.

ASSIGN is out of scope per FR-055.
Reference: MUMPS 1995 ANSI Standard
"""

import pytest


@pytest.mark.parser
class TestAssignCommandParsing:
    """Parser-level tests for ASSIGN command."""

    @pytest.mark.skip(reason="Out of scope per FR-055: ASSIGN command not supported")
    def test_assign_out_of_scope(self):
        """ASSIGN command is out of scope."""
        pass
