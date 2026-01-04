"""Tests for ZBREAK command ASG analysis (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest

from m2py import MUMPSParser
from m2py.asg.statements import MZBreakStatement
from m2py.asg.elements import MCall


@pytest.mark.asg
@pytest.mark.ydb
class TestZbreakAsg:
    """ASG-level tests for ZBREAK command (YDB)."""

    def test_zbreak_asg_node(self):
        """ZBREAK creates proper ASG node with entryref location."""
        parser = MUMPSParser()
        source = """TEST
 ZBREAK SUB^ROUTINE
"""
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MZBreakStatement)
        assert len(stmt.args) == 1
        # Verify location is an MCall (entryref)
        arg = stmt.args[0]
        assert isinstance(arg.location, MCall)
        assert arg.location.name == "SUB"
        assert arg.location.routine == "ROUTINE"

    def test_zbreak_action_analysis(self):
        """ZBREAK action code is analyzed as StringLiteral."""
        parser = MUMPSParser()
        source = """TEST
 ZBREAK SUB^ROUTINE:"W 1"
"""
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MZBreakStatement)
        assert len(stmt.args) == 1
        arg = stmt.args[0]
        # Verify action is a string literal
        assert arg.action is not None
        assert arg.action.value == "W 1"
