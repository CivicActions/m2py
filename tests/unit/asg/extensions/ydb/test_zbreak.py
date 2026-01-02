"""Tests for ZBREAK command ASG analysis (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.asg
@pytest.mark.ydb
class TestZbreakAsg:
    """ASG-level tests for ZBREAK command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZBREAK ASG")
    def test_zbreak_asg_node(self, analyze_statement):
        """ZBREAK creates proper ASG node."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZBREAK action analysis")
    def test_zbreak_action_analysis(self, analyze_statement):
        """ZBREAK action code is analyzed."""
        pytest.fail("Stub - implement test")
