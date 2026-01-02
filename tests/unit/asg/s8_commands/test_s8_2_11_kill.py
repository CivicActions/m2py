"""Tests for KILL command ASG analysis (§8.2.11).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.11
"""

import pytest


@pytest.mark.asg
class TestKillCommandAnalysis:
    """ASG-level tests for KILL command analysis (§8.2.11)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KILL variable tracking")
    def test_kill_variable_tracking(self, analyze_routine):
        """KILL variable is tracked in output_variables (§8.2.11)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KILL exclusive form")
    def test_kill_exclusive_form(self, analyze_routine):
        """KILL (X,Y) exclusive form is analyzed (§8.2.11)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KILL global impact")
    def test_kill_global_impact(self, analyze_routine):
        """KILL ^GLOBAL impact is tracked (§8.2.11)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KILL subscripted")
    def test_kill_subscripted(self, analyze_routine):
        """KILL arr(sub) subscripted kill is analyzed (§8.2.11)."""
        pytest.fail("Stub - implement test")
