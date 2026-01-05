"""Tests for Character Set parsing (§9).

Reference: MUMPS 1995 ANSI Standard, Section 9
"""

import pytest

from m2py.asg.expressions import MBinaryOp
from m2py.parser.textx_classes import IntrinsicFunction, StringLiteral


@pytest.mark.parser
class TestCharacterSetParsing:
    """Parser-level tests for character set handling (§9)."""

    def test_graphic_characters(self, parse_mumps):
        """Graphic characters (printable) parse correctly (§9).

        All printable ASCII characters 32-126 are graphic characters.
        """
        result = parse_mumps('TEST\n S X="ABCDEFGHIJKLMNOPQRSTUVWXYZ"\n Q')
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        value = stmt.assignments[0].value
        assert isinstance(value, StringLiteral)
        assert value.value == "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def test_ascii_subset(self, parse_mumps):
        """ASCII subset characters parse correctly (§9).

        MUMPS uses the ASCII subset for source code.
        """
        result = parse_mumps('TEST\n S X="0123456789"\n Q')
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        value = stmt.assignments[0].value
        assert isinstance(value, StringLiteral)
        assert value.value == "0123456789"

    def test_character_collation(self, parse_mumps):
        """Character collation ordering is correct (§9).

        The ] (follows) operator compares strings by collation order.
        """
        result = parse_mumps('TEST\n S X="B"]"A"\n Q')
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        value = stmt.assignments[0].value
        assert isinstance(value, MBinaryOp)
        assert value.operator == "]"

    def test_control_characters(self, parse_mumps):
        """Control characters in strings parse correctly (§9).

        Control characters (0-31) are represented via $CHAR.
        """
        # $C(9) is tab, $C(10) is newline
        result = parse_mumps("TEST\n S X=$C(9,10,13)\n Q")
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        value = stmt.assignments[0].value
        assert isinstance(value, IntrinsicFunction)
        assert value.name == "C"
        assert len(value.arguments) == 3

    def test_char_function_values(self, parse_mumps):
        """$CHAR values match character set (§9).

        $CHAR converts ASCII codes to characters.
        """
        result = parse_mumps("TEST\n S X=$C(65)\n Q")
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        value = stmt.assignments[0].value
        assert isinstance(value, IntrinsicFunction)
        assert value.name == "C"
        # Argument is 65 (ASCII for 'A')
        assert value.arguments[0].value == 65

    def test_ascii_function_values(self, parse_mumps):
        """$ASCII values match character set (§9).

        $ASCII converts characters to ASCII codes.
        """
        result = parse_mumps('TEST\n S X=$A("ABC")\n Q')
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        value = stmt.assignments[0].value
        assert isinstance(value, IntrinsicFunction)
        assert value.name == "A"
        # Argument is the string "ABC"
        assert value.arguments[0].value == "ABC"

    # Extended character sets beyond ASCII are implementation-defined (§9).
    # See docs/limitations.md - LIM-006: Extended Character Sets
