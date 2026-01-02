"""Tests for ZGOTO command ASG analysis (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.asg
@pytest.mark.ydb
class TestZgotoAsg:
    """ASG-level tests for ZGOTO command (YDB)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZGOTO ASG")
    def test_zgoto_asg_node(self, analyze_statement):
        """ZGOTO creates proper ASG node."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZGotoType classification")
    def test_zgoto_type_classification(self, analyze_statement):
        """ZGOTO is classified by type (unwinding, computed)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZGOTO entryref resolution")
    def test_zgoto_entryref_resolution(self, analyze_statement):
        """ZGOTO entryref is resolved to target."""
        pytest.fail("Stub - implement test")
