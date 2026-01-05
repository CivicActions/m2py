"""Tests for event processing commands parsing.

Event processing commands (ABLOCK, AUNBLOCK, ASTART, ASTOP, ESTART, ESTOP, ETRIGGER)
are not implemented per LIM-001.

Reference: MUMPS 1995 ANSI Standard
See: docs/limitations.md - LIM-001: Event Processing Commands
"""

import pytest

from m2py.asg.elements import MParseError
from m2py.parser.line_parser import parse_line_content


@pytest.mark.parser
class TestEventProcessingCommandsParsing:
    """Parser-level tests for event processing commands.

    These commands are not implemented (LIM-001) and should produce parse errors.
    """

    def test_ablock_raises_parse_error(self):
        """ABLOCK command raises parse error. See LIM-001."""
        result = parse_line_content("ABLOCK")
        assert isinstance(result, MParseError)
        assert "Unknown command" in result.message
        assert "ABLOCK" in result.message

    def test_aunblock_raises_parse_error(self):
        """AUNBLOCK command raises parse error. See LIM-001."""
        result = parse_line_content("AUNBLOCK")
        assert isinstance(result, MParseError)
        assert "Unknown command" in result.message
        assert "AUNBLOCK" in result.message

    def test_astart_raises_parse_error(self):
        """ASTART command raises parse error. See LIM-001."""
        result = parse_line_content("ASTART")
        assert isinstance(result, MParseError)
        assert "Unknown command" in result.message
        assert "ASTART" in result.message

    def test_astop_raises_parse_error(self):
        """ASTOP command raises parse error. See LIM-001."""
        result = parse_line_content("ASTOP")
        assert isinstance(result, MParseError)
        assert "Unknown command" in result.message
        assert "ASTOP" in result.message

    def test_estart_raises_parse_error(self):
        """ESTART command raises parse error. See LIM-001."""
        result = parse_line_content("ESTART")
        assert isinstance(result, MParseError)
        assert "Unknown command" in result.message
        assert "ESTART" in result.message

    def test_estop_raises_parse_error(self):
        """ESTOP command raises parse error. See LIM-001."""
        result = parse_line_content("ESTOP")
        assert isinstance(result, MParseError)
        assert "Unknown command" in result.message
        assert "ESTOP" in result.message

    def test_etrigger_raises_parse_error(self):
        """ETRIGGER command raises parse error. See LIM-001."""
        result = parse_line_content("ETRIGGER")
        assert isinstance(result, MParseError)
        assert "Unknown command" in result.message
        assert "ETRIGGER" in result.message
