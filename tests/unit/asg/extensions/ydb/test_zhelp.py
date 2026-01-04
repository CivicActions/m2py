"""Tests for ZHELP command ASG analysis (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MZHelpStatement


@pytest.fixture
def parser():
    """Provide a MUMPSParser instance."""
    return MUMPSParser()


def parse_statement(parser, code_line):
    """Parse a line of code and return the first statement."""
    source = f"""TEST ; Test routine
 {code_line}
"""
    routine = parser.parse(source)
    return routine.labels[0].body.statements[0]


@pytest.mark.asg
@pytest.mark.ydb
class TestZhelpAsg:
    """ASG-level tests for ZHELP command (YDB)."""

    def test_zhelp_asg_node(self, parser):
        """ZHELP creates proper ASG node."""
        stmt = parse_statement(parser, "ZHELP")
        assert isinstance(stmt, MZHelpStatement)
        assert stmt.args == []

    def test_zhelp_with_topic_asg(self, parser):
        """ZHELP with topic creates MZHelpArg with topic."""
        stmt = parse_statement(parser, 'ZHELP "WRITE"')
        assert isinstance(stmt, MZHelpStatement)
        assert len(stmt.args) == 1
        assert stmt.args[0].topic.value == "WRITE"
        assert stmt.args[0].library is None

    def test_zhelp_with_topic_and_library_asg(self, parser):
        """ZHELP with topic:library creates proper MZHelpArg."""
        stmt = parse_statement(parser, 'ZHELP "MUPIP":"mupip"')
        assert isinstance(stmt, MZHelpStatement)
        assert len(stmt.args) == 1
        assert stmt.args[0].topic.value == "MUPIP"
        assert stmt.args[0].library.value == "mupip"
