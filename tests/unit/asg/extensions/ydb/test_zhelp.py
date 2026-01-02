"""Tests for ZHELP command ASG analysis (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.asg
@pytest.mark.ydb
class TestZhelpAsg:
    """ASG-level tests for ZHELP command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZHELP ASG")
    def test_zhelp_asg_node(self, analyze_statement):
        """ZHELP creates proper ASG node."""
        pytest.fail("Stub - implement test")
