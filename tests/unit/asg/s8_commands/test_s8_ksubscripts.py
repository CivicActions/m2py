"""Tests for $KEY subscripts ASG analysis (§8.2.20).

Shares section numbering with TRESTART.
Reference: MUMPS 1995 ANSI Standard, Section 8.2.20
"""

import pytest


@pytest.mark.asg
class TestKSubscriptsAnalysis:
    """ASG-level tests for $KEY subscripts (§8.2.20)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KSUBSCRIPTS ASG node")
    def test_ksubscripts_asg_node(self, analyze_line):
        """KSUBSCRIPTS produces correct ASG node (§8.2.20)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KSUBSCRIPTS subscript analysis")
    def test_ksubscripts_subscript_analysis(self, analyze_line):
        """KSUBSCRIPTS subscripts are analyzed correctly (§8.2.20)."""
        pytest.fail("Stub - implement test")
