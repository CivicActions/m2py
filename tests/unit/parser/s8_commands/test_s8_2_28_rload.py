"""Tests for RLOAD command parsing (§8.2.28).

RLOAD is not supported. See LIM-009 in docs/limitations.md.
Reference: MUMPS 1995 ANSI Standard, Section 8.2.28
"""

import pytest

from m2py.asg.elements import MParseError
from m2py.parser.line_parser import parse_line_content


@pytest.mark.parser
class TestRloadCommandParsing:
    """Parser-level tests for RLOAD command (§8.2.28)."""

    def test_rload_raises_parse_error(self):
        """RLOAD command raises parse error. See LIM-009."""
        result = parse_line_content("RLOAD ^RTN")
        assert isinstance(result, MParseError)
        assert "Unknown command" in result.message or "RLOAD" in result.message

    def test_rl_abbreviated_raises_parse_error(self):
        """RL (abbreviated RLOAD) raises parse error. See LIM-009."""
        result = parse_line_content("RL ^RTN")
        assert isinstance(result, MParseError)
        assert "Unknown command" in result.message or "RL" in result.message
