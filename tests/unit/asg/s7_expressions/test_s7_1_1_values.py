"""Tests for Values ASG analysis (§7.1.1).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.1
"""

import pytest

from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.expressions import LiteralType
from m2py.parser.line_parser import parse_commands_from_line
from m2py.parser.textx_classes import NumericLiteral, StringLiteral


def analyze_set_command(line: str):
    """Parse a SET command and return the analyzed statement."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestValuesAnalysis:
    """ASG-level tests for values analysis (§7.1.1)."""

    def test_value_type_inference(self):
        """Value types are correctly inferred in ASG (§7.1.1).

        Tests that string literals get STRING type and numeric literals get
        INTEGER or DECIMAL type based on their content.
        """
        # String values get STRING literal_type
        stmt = analyze_set_command('S X="hello"')
        string_val = stmt.assignments[0].value
        assert isinstance(string_val, StringLiteral)
        assert string_val.literal_type == LiteralType.STRING

        # Integer values get INTEGER literal_type
        stmt = analyze_set_command("S X=42")
        int_val = stmt.assignments[0].value
        assert isinstance(int_val, NumericLiteral)
        assert int_val.literal_type == LiteralType.INTEGER

        # Decimal values get DECIMAL literal_type
        stmt = analyze_set_command("S X=3.14")
        dec_val = stmt.assignments[0].value
        assert isinstance(dec_val, NumericLiteral)
        assert dec_val.literal_type == LiteralType.DECIMAL

    def test_string_value_representation(self):
        """String values are correctly represented (§7.1.1).

        Tests that string literals parse to StringLiteral nodes with
        the correct value extracted.
        """
        stmt = analyze_set_command('S X="Hello World"')
        value = stmt.assignments[0].value

        assert isinstance(value, StringLiteral)
        assert value.value == "Hello World"
        assert value.literal_type == LiteralType.STRING

    def test_numeric_value_representation(self):
        """Numeric values are correctly represented (§7.1.1).

        Tests that integer and decimal literals parse to NumericLiteral
        nodes with appropriate types and values.
        """
        # Integer
        stmt = analyze_set_command("S X=123")
        int_val = stmt.assignments[0].value
        assert isinstance(int_val, NumericLiteral)
        assert int_val.value == 123
        assert int_val.literal_type == LiteralType.INTEGER

        # Decimal
        stmt = analyze_set_command("S X=45.67")
        dec_val = stmt.assignments[0].value
        assert isinstance(dec_val, NumericLiteral)
        assert dec_val.value == 45.67
        assert dec_val.literal_type == LiteralType.DECIMAL

    def test_empty_string_representation(self):
        """Empty string values are correctly represented (§7.1.1).

        Tests that empty string ("") parses to StringLiteral with empty value.
        """
        stmt = analyze_set_command('S X=""')
        value = stmt.assignments[0].value

        assert isinstance(value, StringLiteral)
        assert value.value == ""
        assert value.literal_type == LiteralType.STRING
