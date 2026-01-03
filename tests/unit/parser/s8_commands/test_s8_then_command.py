"""Tests for THEN command parsing (§8.2.32).

THEN is out of scope per FR-055 (zero real-world usage).
Reference: MUMPS 1995 ANSI Standard, Section 8.2.32
"""

import pytest


@pytest.mark.parser
class TestThenCommandParsing:
    """Parser-level tests for THEN command (§8.2.32)."""

    @pytest.mark.skip(
        reason="Out of scope per FR-055: THEN command has zero real-world usage"
    )
    def test_then_out_of_scope(self):
        """THEN command is out of scope (§8.2.32)."""
        pass
