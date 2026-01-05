"""Tests for ASSIGN command parsing.

ASSIGN is out of scope per LIM-013 and raises parse error.
Reference: MUMPS 1995 ANSI Standard
Limitation: docs/limitations.md - LIM-013: ASSIGN Command
"""

import pytest

from m2py.asg.elements import MParseError
from m2py.parser.line_parser import parse_line_content


@pytest.mark.parser
class TestAssignCommandParsing:
    """Parser-level tests for ASSIGN command."""

    def test_assign_raises_parse_error(self):
        """ASSIGN command raises parse error. See LIM-013."""
        result = parse_line_content("ASSIGN ^$SYSTEM")
        assert isinstance(result, MParseError)
        assert "Unknown command" in result.message
