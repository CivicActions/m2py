"""Tests for RLOAD command parsing (§8.2.28).

RLOAD is out of scope per FR-055.
Reference: MUMPS 1995 ANSI Standard, Section 8.2.28
"""

import pytest


@pytest.mark.parser
class TestRloadCommandParsing:
    """Parser-level tests for RLOAD command (§8.2.28)."""

    @pytest.mark.skip(reason="Out of scope per FR-055: RLOAD command not supported")
    def test_rload_out_of_scope(self):
        """RLOAD command is out of scope (§8.2.28)."""
        pass
