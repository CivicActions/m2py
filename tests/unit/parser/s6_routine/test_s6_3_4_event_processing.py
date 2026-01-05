"""Tests for Event Processing parsing (§6.3.4).

Event processing commands are not implemented per LIM-001.

Reference: MUMPS 1995 ANSI Standard, Section 6.3.4
See: docs/limitations.md - LIM-001: Event Processing Commands
"""

import pytest

from m2py.asg.elements import MParseError
from m2py.parser.line_parser import parse_line_content


@pytest.mark.parser
class TestEventProcessingParsing:
    """Tests for Event Processing (§6.3.4).

    Event processing commands (ABLOCK, AUNBLOCK, ASTART, ASTOP, ESTART, ESTOP, ETRIGGER)
    are not implemented per LIM-001 and raise parse errors.
    """

    def test_event_processing_commands_raise_parse_error(self):
        """§6.3.4 Event Processing commands raise parse errors. See LIM-001."""
        commands = [
            "ABLOCK",
            "AUNBLOCK",
            "ASTART",
            "ASTOP",
            "ESTART",
            "ESTOP",
            "ETRIGGER",
        ]
        for cmd in commands:
            result = parse_line_content(cmd)
            assert isinstance(result, MParseError), f"{cmd} should raise parse error"
            assert "Unknown command" in result.message
