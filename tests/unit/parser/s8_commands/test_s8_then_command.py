"""Tests for THEN command parsing (§8.2.32).

THEN is out of scope per LIM-002 and raises parse error.
Reference: MUMPS 1995 ANSI Standard, Section 8.2.32
Limitation: docs/limitations.md - LIM-002: THEN Command
"""

import pytest

from m2py.asg.elements import MParseError
from m2py.parser.line_parser import parse_line_content


@pytest.mark.parser
class TestThenCommandParsing:
    """Parser-level tests for THEN command (§8.2.32)."""

    def test_then_raises_parse_error(self):
        """THEN command raises parse error. See LIM-002."""
        result = parse_line_content("THEN W 1")
        assert isinstance(result, MParseError)
        assert "Unknown command" in result.message
