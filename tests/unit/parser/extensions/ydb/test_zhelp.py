"""Tests for ZHELP command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest

from m2py.parser import MUMPSParser


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


@pytest.mark.parser
@pytest.mark.ydb
class TestZhelpParsing:
    """Parser-level tests for ZHELP command (YDB)."""

    def test_zhelp_basic(self, parser):
        """ZHELP parses without error."""
        stmt = parse_statement(parser, "ZHELP")
        assert type(stmt).__name__ == "MZHelpStatement"
        assert stmt.args == []

    def test_zhelp_with_topic(self, parser):
        """ZHELP with topic parses correctly."""
        stmt = parse_statement(parser, 'ZHELP "WRITE"')
        assert type(stmt).__name__ == "MZHelpStatement"
        assert len(stmt.args) == 1
        assert stmt.args[0].topic is not None
        assert stmt.args[0].topic.value == "WRITE"

    def test_zhelp_with_topic_and_library(self, parser):
        """ZHELP with topic and library parses correctly."""
        stmt = parse_statement(parser, 'ZHELP "MUPIP":"mupip"')
        assert type(stmt).__name__ == "MZHelpStatement"
        assert len(stmt.args) == 1
        assert stmt.args[0].topic.value == "MUPIP"
        assert stmt.args[0].library.value == "mupip"

    def test_zhe_abbreviation(self, parser):
        """ZHE abbreviation parses as ZHELP."""
        stmt = parse_statement(parser, 'ZHE "WRITE"')
        assert type(stmt).__name__ == "MZHelpStatement"
