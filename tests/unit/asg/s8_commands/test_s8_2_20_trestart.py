"""Tests for TRESTART command ASG analysis (§8.2.20).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.20
"""

import pytest


@pytest.mark.asg
class TestTrestartCommandAnalysis:
    """ASG-level tests for TRESTART command analysis (§8.2.20)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: TRESTART command node")
    def test_trestart_command_node(self, analyze_routine):
        """TRESTART command creates correct ASG node (§8.2.20)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: TRESTART control flow")
    def test_trestart_control_flow(self, analyze_routine):
        """TRESTART control flow impact is analyzed (§8.2.20)."""
        pytest.fail("Stub - implement test")
