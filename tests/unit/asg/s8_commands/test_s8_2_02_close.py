"""Tests for CLOSE command ASG analysis (§8.2.2).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.2
"""

import pytest


@pytest.mark.asg
class TestCloseCommandAnalysis:
    """ASG-level tests for CLOSE command analysis (§8.2.2)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: CLOSE command node")
    def test_close_command_node(self, analyze_routine):
        """CLOSE command creates correct ASG node (§8.2.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: CLOSE device tracking")
    def test_close_device_tracking(self, analyze_routine):
        """CLOSE device expression is tracked (§8.2.2)."""
        pytest.fail("Stub - implement test")
