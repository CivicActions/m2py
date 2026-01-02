"""Tests for FOR command ASG analysis (§8.2.5).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.5
"""

import pytest


@pytest.mark.asg
class TestForCommandAnalysis:
    """ASG-level tests for FOR command analysis (§8.2.5)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR loop_type classification")
    def test_for_loop_type_classification(self, analyze_routine):
        """FOR loop_type is correctly classified (§8.2.5, FR-012)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR counted loop")
    def test_for_counted_loop(self, analyze_routine):
        """FOR counted loop (start:increment:limit) is analyzed (§8.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR list loop")
    def test_for_list_loop(self, analyze_routine):
        """FOR list loop (val1,val2,val3) is analyzed (§8.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR infinite loop")
    def test_for_infinite_loop(self, analyze_routine):
        """FOR infinite loop (argumentless) is analyzed (§8.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR loop variable")
    def test_for_loop_variable(self, analyze_routine):
        """FOR loop variable is tracked (§8.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR nested loops")
    def test_for_nested_loops(self, analyze_routine):
        """Nested FOR loops are correctly analyzed (§8.2.5)."""
        pytest.fail("Stub - implement test")
