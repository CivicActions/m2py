"""Tests for ZKILL/ZWITHDRAW command ASG analysis (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest

from m2py import MUMPSParser
from m2py.asg.statements import MZKillStatement, MZWithdrawStatement
from m2py.parser.textx_classes import LocalVariable


@pytest.mark.asg
@pytest.mark.ydb
class TestZkillAsg:
    """ASG-level tests for ZKILL/ZWITHDRAW command (YDB)."""

    def test_zkill_asg_node(self):
        """ZKILL creates proper ASG node with targets."""
        parser = MUMPSParser()
        source = """TEST
 ZKILL A(1)
"""
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MZKillStatement)
        assert len(stmt.targets) == 1
        # Verify target is a local variable with subscript
        target = stmt.targets[0]
        assert isinstance(target, LocalVariable)
        assert target.name == "A"
        assert len(target.subscripts) == 1

    def test_zwithdraw_asg_node(self):
        """ZWITHDRAW creates proper ASG node with targets (alias for ZKILL)."""
        parser = MUMPSParser()
        source = """TEST
 ZWITHDRAW A(1)
"""
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MZWithdrawStatement)
        assert len(stmt.targets) == 1
        # ZWITHDRAW is functionally identical to ZKILL
        target = stmt.targets[0]
        assert isinstance(target, LocalVariable)
        assert target.name == "A"
