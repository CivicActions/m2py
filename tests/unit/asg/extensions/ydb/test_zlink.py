"""Tests for ZLINK command ASG analysis (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.asg
@pytest.mark.ydb
class TestZlinkAsg:
    """ASG-level tests for ZLINK command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZLINK ASG")
    def test_zlink_asg_node(self, analyze_statement):
        """ZLINK creates proper ASG node."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZLINK routine tracking")
    def test_zlink_routine_tracking(self, analyze_statement):
        """ZLINK tracks linked routine."""
        pytest.fail("Stub - implement test")
