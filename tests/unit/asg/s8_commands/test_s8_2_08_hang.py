"""Tests for HANG command ASG analysis (§8.2.8).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.8
"""

import pytest


@pytest.mark.asg
class TestHangCommandAnalysis:
    """ASG-level tests for HANG command analysis (§8.2.8)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: HANG command node")
    def test_hang_command_node(self, analyze_routine):
        """HANG command creates correct ASG node (§8.2.8)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: HANG duration expression")
    def test_hang_duration_expression(self, analyze_routine):
        """HANG duration expression is analyzed (§8.2.8)."""
        pytest.fail("Stub - implement test")
