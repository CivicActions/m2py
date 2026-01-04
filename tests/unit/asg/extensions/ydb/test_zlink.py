"""Tests for ZLINK command ASG analysis (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest

from m2py import MUMPSParser
from m2py.asg.statements import MZLinkStatement
from m2py.parser.textx_classes import StringLiteral


@pytest.mark.asg
@pytest.mark.ydb
class TestZlinkAsg:
    """ASG-level tests for ZLINK command (YDB)."""

    def test_zlink_asg_node(self):
        """ZLINK creates proper ASG node with routine file argument."""
        parser = MUMPSParser()
        source = """TEST
 ZLINK "test"
"""
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MZLinkStatement)
        assert len(stmt.args) == 1
        # Verify argument is a string literal with routine name
        assert isinstance(stmt.args[0], StringLiteral)
        assert stmt.args[0].value == "test"

    def test_zlink_routine_tracking(self):
        """ZLINK tracks linked routine with .m extension."""
        parser = MUMPSParser()
        source = """TEST
 ZLINK "myutil.m"
"""
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MZLinkStatement)
        assert len(stmt.args) == 1
        # Routine with explicit .m extension
        assert stmt.args[0].value == "myutil.m"
