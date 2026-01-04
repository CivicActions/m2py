"""Tests for ZTRIGGER command ASG analysis (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest

from m2py import MUMPSParser
from m2py.asg.statements import MZTriggerStatement
from m2py.parser.textx_classes import GlobalVariable


@pytest.mark.asg
@pytest.mark.ydb
class TestZtriggerAsg:
    """ASG-level tests for ZTRIGGER command (YDB)."""

    def test_ztrigger_asg_node(self):
        """ZTRIGGER creates proper ASG node with global variable target."""
        parser = MUMPSParser()
        source = """TEST
 ZTRIGGER ^C
"""
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MZTriggerStatement)
        assert len(stmt.targets) == 1
        # Verify target is a global variable
        target = stmt.targets[0]
        assert isinstance(target, GlobalVariable)
        assert target.name == "C"
