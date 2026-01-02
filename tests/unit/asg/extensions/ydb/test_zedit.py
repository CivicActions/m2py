"""Tests for ZEDIT command ASG analysis (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.asg
@pytest.mark.ydb
class TestZeditAsg:
    """ASG-level tests for ZEDIT command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZEDIT ASG")
    def test_zedit_asg_node(self, analyze_statement):
        """ZEDIT creates proper ASG node."""
        pytest.fail("Stub - implement test")
