"""Tests for ZHALT command ASG analysis (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest

from m2py import MUMPSParser
from m2py.asg.statements import MZHaltStatement


@pytest.mark.asg
@pytest.mark.ydb
class TestZhaltAsg:
    """ASG-level tests for ZHALT command (YDB)."""

    def test_zhalt_asg_node(self):
        """ZHALT creates proper ASG node."""
        parser = MUMPSParser()
        source = """TEST
 ZHALT
"""
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MZHaltStatement)
        # ZHALT without argument has no exitcode
        assert stmt.exitcode is None

    def test_zhalt_status_tracking(self):
        """ZHALT exit status is tracked in exitcode attribute."""
        parser = MUMPSParser()
        source = """TEST
 ZHALT 230
"""
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MZHaltStatement)
        # ZHALT with argument tracks exit code
        assert stmt.exitcode is not None
        assert stmt.exitcode.value == 230
