"""Tests for Literals ASG analysis (§7.1.4).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.4
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
class TestLiteralsAnalysis:
    """ASG-level tests for literals analysis (§7.1.4)."""

    def test_integer_literal(self):
        """Integer literals are correctly represented (§7.1.4).

        Tests that integer values parse to NumericLiteral with INTEGER type.
        """
        stmt = analyze_set_command("S X=42")
        value = stmt.assignments[0].value

        assert isinstance(value, NumericLiteral)
        assert value.value == 42
        assert value.literal_type == LiteralType.INTEGER

    def test_decimal_literal(self):
        """Decimal literals are correctly represented (§7.1.4).

        Tests that decimal values parse to NumericLiteral with DECIMAL type.
        """
        stmt = analyze_set_command("S X=3.14159")
        value = stmt.assignments[0].value

        assert isinstance(value, NumericLiteral)
        assert value.value == 3.14159
        assert value.literal_type == LiteralType.DECIMAL

    def test_string_literal(self):
        """String literals are correctly represented (§7.1.4).

        Tests that quoted strings parse to StringLiteral with STRING type.
        """
        stmt = analyze_set_command('S X="Hello World"')
        value = stmt.assignments[0].value

        assert isinstance(value, StringLiteral)
        assert value.value == "Hello World"
        assert value.literal_type == LiteralType.STRING

    def test_escaped_quotes(self):
        """Escaped quotes in strings are correctly handled (§7.1.4).

        In MUMPS, quotes are escaped by doubling them ("").
        """
        # "He said ""Hello""" should become: He said "Hello"
        stmt = analyze_set_command('S X="He said ""Hello"""')
        value = stmt.assignments[0].value

        assert isinstance(value, StringLiteral)
        assert value.value == 'He said "Hello"'
        assert value.literal_type == LiteralType.STRING

    def test_numeric_string_literal(self):
        """Numeric string literals type is correctly inferred (§7.1.4).

        A string containing numeric characters is still a StringLiteral,
        not a NumericLiteral. Type coercion happens at runtime.
        """
        stmt = analyze_set_command('S X="123"')
        value = stmt.assignments[0].value

        assert isinstance(value, StringLiteral)
        assert value.value == "123"
        assert value.literal_type == LiteralType.STRING

    def test_empty_string_literal(self):
        """Empty string literals are correctly represented (§7.1.4).

        Tests that "" parses to StringLiteral with empty value.
        """
        stmt = analyze_set_command('S X=""')
        value = stmt.assignments[0].value

        assert isinstance(value, StringLiteral)
        assert value.value == ""
        assert value.literal_type == LiteralType.STRING

    def test_scientific_notation(self):
        """Scientific notation literals are correctly handled (§7.1.4).

        Tests that scientific notation (e.g., 1.5E10) parses to NumericLiteral
        with the computed value and DECIMAL type.
        """
        stmt = analyze_set_command("S X=1.5E10")
        value = stmt.assignments[0].value

        assert isinstance(value, NumericLiteral)
        assert value.value == 1.5e10
        assert value.literal_type == LiteralType.DECIMAL
