"""Tests for ZKILL/ZWITHDRAW command ASG analysis (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.asg
@pytest.mark.ydb
class TestZkillAsg:
    """ASG-level tests for ZKILL/ZWITHDRAW command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZKILL ASG")
    def test_zkill_asg_node(self, analyze_statement):
        """ZKILL creates proper ASG node."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZWITHDRAW ASG")
    def test_zwithdraw_asg_node(self, analyze_statement):
        """ZWITHDRAW creates proper ASG node."""
        pytest.fail("Stub - implement test")
