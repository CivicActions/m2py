"""Tests for character set definitions parsing (§9.1).

Reference: MUMPS 1995 ANSI Standard, Section 9.1
"""

import pytest

from m2py.asg import MSetStatement, MWriteStatement
from m2py.parser.textx_classes import LocalVariable, StringLiteral


@pytest.mark.parser
class TestCharacterSetDefinitionsParsing:
    """Parser-level tests for character set definitions (§9.1)."""

    def test_ascii_characters(self, parse_mumps):
        """ASCII characters are handled correctly (§9.1).

        Standard ASCII printable characters parse in strings and identifiers.
        """
        result = parse_mumps('TEST\n S X="Hello World 123!@#"\n Q')
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        assert isinstance(stmt, MSetStatement)
        value = stmt.assignments[0].value
        assert isinstance(value, StringLiteral)
        assert value.value == "Hello World 123!@#"

    def test_control_characters(self, parse_mumps):
        """Control characters are handled correctly (§9.1).

        Control characters are embedded via $CHAR function.
        """
        # $C(10) is newline, $C(13) is carriage return
        result = parse_mumps('TEST\n W "Line1",$C(10),"Line2"\n Q')
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        assert isinstance(stmt, MWriteStatement)
        # Three write arguments: string, $C(10), string
        assert len(stmt.arguments) == 3

    def test_graphic_characters(self, parse_mumps):
        """Graphic characters are handled correctly (§9.1).

        All printable ASCII characters (graphic characters) parse in strings.
        """
        # Test a variety of graphic characters
        result = parse_mumps('TEST\n S X="abcABC123!@#$%^&*()"\n Q')
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        assert isinstance(stmt, MSetStatement)
        value = stmt.assignments[0].value
        assert isinstance(value, StringLiteral)

    def test_special_characters(self, parse_mumps):
        """Special characters in identifiers are handled correctly (§9.1).

        The % character is valid as the first character of a variable name.
        """
        result = parse_mumps("TEST\n S %X=1\n S %ZOSV=2\n Q")
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        assert isinstance(stmt, MSetStatement)
        target = stmt.assignments[0].target
        assert isinstance(target, LocalVariable)
        assert target.name == "%X"
