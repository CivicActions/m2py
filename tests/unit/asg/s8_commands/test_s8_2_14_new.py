"""Tests for NEW command ASG analysis (§8.2.14).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.14
"""

import pytest


@pytest.mark.asg
class TestNewCommandAnalysis:
    """ASG-level tests for NEW command analysis (§8.2.14)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW variable scoping")
    def test_new_variable_scoping(self, analyze_routine):
        """NEW creates new variable scope (§8.2.14, FR-014)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW exclusive form")
    def test_new_exclusive_form(self, analyze_routine):
        """NEW (X,Y) exclusive form is analyzed (§8.2.14)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW scope lifetime")
    def test_new_scope_lifetime(self, analyze_routine):
        """NEW scope lifetime is tracked until QUIT (§8.2.14)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW multiple variables")
    def test_new_multiple_variables(self, analyze_routine):
        """NEW X,Y,Z multiple variables is analyzed (§8.2.14)."""
        pytest.fail("Stub - implement test")
