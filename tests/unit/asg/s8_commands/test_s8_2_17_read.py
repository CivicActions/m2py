"""Tests for READ command ASG analysis (§8.2.17).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.17
"""

import pytest


@pytest.mark.asg
class TestReadCommandAnalysis:
    """ASG-level tests for READ command analysis (§8.2.17)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ variable tracking")
    def test_read_variable_tracking(self, analyze_routine):
        """READ variable is tracked in output_variables (§8.2.17)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ format controls")
    def test_read_format_controls(self, analyze_routine):
        """READ format controls (!, ?, #) are analyzed (§8.2.17)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ timeout")
    def test_read_timeout(self, analyze_routine):
        """READ timeout expression is analyzed (§8.2.17)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ single character")
    def test_read_single_character(self, analyze_routine):
        """READ *X single character is analyzed (§8.2.17)."""
        pytest.fail("Stub - implement test")
