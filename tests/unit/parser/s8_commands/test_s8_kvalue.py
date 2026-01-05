"""Tests for KVALUE command parsing (§8.2.21).

KVALUE kills only values, preserving subscripts (descendants).
Reference: MUMPS 1995 ANSI Standard, Section 8.2.21
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line


@pytest.mark.parser
class TestKValueParsing:
    """Parser-level tests for KVALUE (§8.2.21)."""

    def test_kvalue_basic(self):
        """KVALUE parses correctly (§8.2.21)."""
        # Abbreviated form
        cmds = parse_commands_from_line("KV X")
        assert len(cmds) == 1
        assert type(cmds[0]).__name__ == "KValueCommand"

        # Full spelling
        cmds2 = parse_commands_from_line("KVALUE X")
        assert len(cmds2) == 1
        assert type(cmds2[0]).__name__ == "KValueCommand"

    def test_kvalue_with_arguments(self):
        """KVALUE with arguments parses correctly (§8.2.21)."""
        # Multiple targets
        cmds = parse_commands_from_line("KV X,Y,Z")
        assert len(cmds) == 1
        assert len(cmds[0].args) == 3

        # Exclusive form
        cmds2 = parse_commands_from_line("KV (A,B)")
        assert len(cmds2) == 1
        assert cmds2[0].args[0].exclusive is True  # exclusive is a boolean flag

        # No arguments (kill all)
        cmds3 = parse_commands_from_line("KV")
        assert len(cmds3) == 1
        assert len(cmds3[0].args) == 0

        # Subscripted target
        cmds4 = parse_commands_from_line("KV X(1,2)")
        assert len(cmds4) == 1
        assert cmds4[0].args[0].target is not None
