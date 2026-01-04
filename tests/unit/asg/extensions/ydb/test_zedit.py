"""Tests for ZEDIT command ASG analysis (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest

from m2py import MUMPSParser
from m2py.asg.statements import MZEditStatement
from m2py.parser.textx_classes import StringLiteral


@pytest.mark.asg
@pytest.mark.ydb
class TestZeditAsg:
    """ASG-level tests for ZEDIT command (YDB)."""

    def test_zedit_asg_node(self):
        """ZEDIT creates proper ASG node with file argument."""
        parser = MUMPSParser()
        source = """TEST
 ZEDIT "BAL"
"""
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MZEditStatement)
        assert len(stmt.args) == 1
        # Verify argument is a string literal with file name
        assert isinstance(stmt.args[0], StringLiteral)
        assert stmt.args[0].value == "BAL"
