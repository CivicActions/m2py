"""Tests for $KEY value ASG analysis (§8.2.21).

Shares section numbering with TROLLBACK.
Reference: MUMPS 1995 ANSI Standard, Section 8.2.21
"""

import pytest


@pytest.mark.asg
class TestKValueAnalysis:
    """ASG-level tests for $KEY value (§8.2.21)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KVALUE ASG node")
    def test_kvalue_asg_node(self, analyze_line):
        """KVALUE produces correct ASG node (§8.2.21)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KVALUE expression analysis")
    def test_kvalue_expression_analysis(self, analyze_line):
        """KVALUE expression is analyzed correctly (§8.2.21)."""
        pytest.fail("Stub - implement test")
