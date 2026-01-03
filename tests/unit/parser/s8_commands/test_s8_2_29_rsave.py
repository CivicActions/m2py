"""Tests for RSAVE command parsing (§8.2.29).

RSAVE is out of scope per FR-055.
Reference: MUMPS 1995 ANSI Standard, Section 8.2.29
"""

import pytest


@pytest.mark.parser
class TestRsaveCommandParsing:
    """Parser-level tests for RSAVE command (§8.2.29)."""

    @pytest.mark.skip(reason="Out of scope per FR-055: RSAVE command not supported")
    def test_rsave_out_of_scope(self):
        """RSAVE command is out of scope (§8.2.29)."""
        pass
