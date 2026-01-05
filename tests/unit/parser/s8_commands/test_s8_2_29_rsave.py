"""Tests for RSAVE command parsing (§8.2.29).

RSAVE is not supported. See LIM-009 in docs/limitations.md.
Reference: MUMPS 1995 ANSI Standard, Section 8.2.29
"""

import pytest

from m2py.asg.elements import MParseError
from m2py.parser.line_parser import parse_line_content


@pytest.mark.parser
class TestRsaveCommandParsing:
    """Parser-level tests for RSAVE command (§8.2.29)."""

    def test_rsave_raises_parse_error(self):
        """RSAVE command raises parse error. See LIM-009."""
        result = parse_line_content("RSAVE ^RTN")
        assert isinstance(result, MParseError)
        assert "Unknown command" in result.message or "RSAVE" in result.message

    def test_rs_abbreviated_raises_parse_error(self):
        """RS (abbreviated RSAVE) raises parse error. See LIM-009."""
        result = parse_line_content("RS ^RTN")
        assert isinstance(result, MParseError)
        assert "Unknown command" in result.message or "RS" in result.message
