"""Tests for ZWRITE command ASG analysis (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest

from m2py import MUMPSParser
from m2py.asg.statements import MZWriteStatement


@pytest.mark.asg
@pytest.mark.ydb
class TestZwriteAsg:
    """ASG-level tests for ZWRITE command (YDB)."""

    def test_zwrite_asg_node(self):
        """ZWRITE creates proper ASG node with variable arguments."""
        parser = MUMPSParser()
        source = """TEST
 ZWRITE A
"""
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MZWriteStatement)
        assert len(stmt.args) == 1
        # Verify argument contains target variable info
        arg = stmt.args[0]
        assert arg.target is not None
        assert arg.target.name == "A"

    def test_zwrite_variable_analysis(self):
        """ZWRITE variable reference is analyzed with subscripts."""
        parser = MUMPSParser()
        source = """TEST
 ZWRITE X(1,2)
"""
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MZWriteStatement)
        assert len(stmt.args) == 1
        # Verify subscripted variable is captured
        arg = stmt.args[0]
        assert arg.target.name == "X"
        # The target should have subscript info
        assert len(arg.target.subscripts) == 2
