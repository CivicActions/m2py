"""Tests for Routine Head ASG analysis (§6.1).

Reference: MUMPS 1995 ANSI Standard, Section 6.1
"""

import pytest


@pytest.mark.asg
class TestRoutineHeadAnalysis:
    """ASG-level tests for routine head analysis (§6.1)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: routine name extraction")
    def test_routine_name_extraction(self, analyze_routine):
        """Routine name is correctly extracted to ASG (§6.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: formal parameter list")
    def test_formal_parameter_list(self, analyze_routine):
        """Formal parameter list is correctly analyzed (§6.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: routine metadata")
    def test_routine_metadata(self, analyze_routine):
        """Routine metadata is captured in ASG (§6.1)."""
        pytest.fail("Stub - implement test")
