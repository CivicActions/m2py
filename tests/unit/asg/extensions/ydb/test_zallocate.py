"""Tests for ZALLOCATE/ZDEALLOCATE command ASG analysis (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.asg
@pytest.mark.ydb
class TestZallocateAsg:
    """ASG-level tests for ZALLOCATE/ZDEALLOCATE command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZALLOCATE ASG")
    def test_zallocate_asg_node(self, analyze_statement):
        """ZALLOCATE creates proper ASG node."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZDEALLOCATE ASG")
    def test_zdeallocate_asg_node(self, analyze_statement):
        """ZDEALLOCATE creates proper ASG node."""
        pytest.fail("Stub - implement test")
