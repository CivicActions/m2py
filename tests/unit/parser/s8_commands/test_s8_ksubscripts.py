"""Tests for KSUBSCRIPTS command parsing (§8.2.20).

KSUBSCRIPTS kills only subscripts (descendants), preserving values.
Reference: MUMPS 1995 ANSI Standard, Section 8.2.20
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line


@pytest.mark.parser
class TestKSubscriptsParsing:
    """Parser-level tests for KSUBSCRIPTS (§8.2.20)."""

    def test_ksubscripts_basic(self):
        """KSUBSCRIPTS parses correctly (§8.2.20)."""
        # Abbreviated form
        cmds = parse_commands_from_line("KS X")
        assert len(cmds) == 1
        assert type(cmds[0]).__name__ == "KSubscriptsCommand"

        # Full spelling
        cmds2 = parse_commands_from_line("KSUBSCRIPTS X")
        assert len(cmds2) == 1
        assert type(cmds2[0]).__name__ == "KSubscriptsCommand"

    def test_ksubscripts_with_arguments(self):
        """KSUBSCRIPTS with arguments parses correctly (§8.2.20)."""
        # Multiple targets
        cmds = parse_commands_from_line("KS X,Y,Z")
        assert len(cmds) == 1
        assert len(cmds[0].args) == 3

        # Exclusive form
        cmds2 = parse_commands_from_line("KS (A,B)")
        assert len(cmds2) == 1
        assert cmds2[0].args[0].exclusive is True  # exclusive is a boolean flag

        # No arguments (kill all)
        cmds3 = parse_commands_from_line("KS")
        assert len(cmds3) == 1
        assert len(cmds3[0].args) == 0

        # Subscripted target
        cmds4 = parse_commands_from_line("KS X(1,2)")
        assert len(cmds4) == 1
        assert cmds4[0].args[0].target is not None
