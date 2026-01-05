"""Tests for out-of-scope commands parsing.

These commands are part of the ANSI spec but are not implemented.
Each test verifies that parse errors are raised correctly.

See docs/limitations.md for limitation IDs:
- LIM-001: Event Processing Commands (ESTART, ESTOP, ETRIGGER)
- LIM-009: RLOAD/RSAVE Commands
"""

import pytest

from m2py.asg.elements import MParseError
from m2py.parser.line_parser import parse_line_content


@pytest.mark.parser
class TestOutOfScopeCommands:
    """Parser-level tests for commands that are not implemented."""

    def test_estart_raises_parse_error(self):
        """ESTART command raises parse error. See LIM-001."""
        result = parse_line_content("ESTART")
        assert isinstance(result, MParseError)
        assert "Unknown command" in result.message

    def test_estop_raises_parse_error(self):
        """ESTOP command raises parse error. See LIM-001."""
        result = parse_line_content("ESTOP")
        assert isinstance(result, MParseError)
        assert "Unknown command" in result.message

    def test_etrigger_raises_parse_error(self):
        """ETRIGGER command raises parse error. See LIM-001."""
        result = parse_line_content("ETRIGGER")
        assert isinstance(result, MParseError)
        assert "Unknown command" in result.message

    def test_rload_raises_parse_error(self):
        """RLOAD command raises parse error. See LIM-009."""
        result = parse_line_content("RLOAD ^RTN")
        assert isinstance(result, MParseError)
        assert "Unknown command" in result.message or "RLOAD" in result.message

    def test_rsave_raises_parse_error(self):
        """RSAVE command raises parse error. See LIM-009."""
        result = parse_line_content("RSAVE ^RTN")
        assert isinstance(result, MParseError)
        assert "Unknown command" in result.message or "RSAVE" in result.message
