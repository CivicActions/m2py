"""Tests for RLOAD command ASG analysis.

RLOAD is out of scope per FR-055.
Reference: MUMPS 1995 ANSI Standard
"""

import pytest


@pytest.mark.asg
class TestRloadCommandAnalysis:
    """ASG-level tests for RLOAD command."""

    @pytest.mark.skip(reason="Out of scope per FR-055: RLOAD command not supported")
    def test_rload_out_of_scope(self):
        """RLOAD command is out of scope."""
        pass
