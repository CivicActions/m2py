"""Tests for RSAVE command ASG analysis.

RSAVE is out of scope per FR-055.
Reference: MUMPS 1995 ANSI Standard
"""

import pytest


@pytest.mark.asg
class TestRsaveCommandAnalysis:
    """ASG-level tests for RSAVE command."""

    @pytest.mark.skip(reason="Out of scope per FR-055: RSAVE command not supported")
    def test_rsave_out_of_scope(self):
        """RSAVE command is out of scope."""
        pass
