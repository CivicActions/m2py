"""Tests for Character Set ASG analysis (§9).

Reference: MUMPS 1995 ANSI Standard, Section 9
Charset M (Annex A) - 1995__aa01001.md

§9 defines the Character Set Profile which specifies:
1. Character codes and their meaning (ASCII 0-127 for charset M)
2. Valid name characters (patcode A chars)
3. Available patcodes (A, C, E, L, N, P, U)
4. Collation order for string comparison
"""

import pytest

from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.expressions import MBinaryOp, LiteralType
from m2py.parser.line_parser import parse_commands_from_line
from m2py.parser.textx_classes import StringLiteral


def get_expression_from_set(line: str):
    """Parse a SET command and return the value expression from first assignment."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    stmt = analyze_command(cmds[0])
    assert len(stmt.assignments) >= 1, "No assignments in SET command"
    return stmt.assignments[0].value


@pytest.mark.asg
class TestCharacterSetAnalysis:
    """ASG-level tests for character set handling (§9).

    Note: These tests complement s7_expressions tests by focusing on
    charset-specific behavior with string literals rather than variables.
    """

    def test_character_encoding(self, analyze_expression):
        """Character encoding is correctly handled in ASG (§9).

        From spec (1995__aa01001): Charset M uses ASCII codes 0-127.
        String literals should preserve all ASCII characters including:
        - Control chars (C patcode): ASCII 0-31, 127
        - Printable chars (P patcode): punctuation
        - Letters (A patcode): A-Z, a-z
        - Digits (N patcode): 0-9

        Tests that string literals with special characters are correctly
        represented in the ASG.
        """
        # Test punctuation and special characters (P patcode)
        stmt = analyze_command(
            parse_commands_from_line('S X="!@#$%^&*()_+-=[]{}|;:,.<>?"')[0]
        )
        value = stmt.assignments[0].value

        assert isinstance(value, StringLiteral)
        assert value.value == "!@#$%^&*()_+-=[]{}|;:,.<>?"
        assert value.literal_type == LiteralType.STRING

        # Test mixed character classes (A, N, P)
        stmt2 = analyze_command(parse_commands_from_line('S Y="ABC123!@#xyz789"')[0])
        value2 = stmt2.assignments[0].value

        assert isinstance(value2, StringLiteral)
        assert value2.value == "ABC123!@#xyz789"

    def test_collation_order(self, analyze_expression):
        """Collation order is correctly analyzed (§9).

        From spec (1995__aa01001): The collation function CO defines string ordering:
        1. CO("",s) = s - Empty string sorts first
        2. CO(m,n) = n if n > m - Numeric strings sort numerically
        3. CO(m,u) = u - Numeric sorts before non-numeric
        4. CO(u,v) = v if v ] u - Non-numeric strings sort by ASCII position

        The ]] operator (collates after) tests subscript collation order.
        This test verifies ]] with string literals produces correct ASG.
        """
        # Test collation after (]]) with string literals
        # "AB" collates after "AA" in ASCII order
        value = get_expression_from_set('S X="AB"]]"AA"')

        assert isinstance(value, MBinaryOp)
        assert value.operator == "]]"
        assert isinstance(value.left, StringLiteral)
        assert isinstance(value.right, StringLiteral)
        assert value.left.value == "AB"
        assert value.right.value == "AA"

        # Numeric string collation - "10" ]] "2" (numeric comparison)
        value2 = get_expression_from_set('S X="10"]]"2"')

        assert isinstance(value2, MBinaryOp)
        assert value2.operator == "]]"
        assert value2.left.value == "10"
        assert value2.right.value == "2"

    def test_string_comparison(self, analyze_expression):
        """String comparison respects character set (§9).

        From spec (1977__a107197): A]B is true if A follows B in ASCII collating sequence.
        This differs from ]] (collates after) in handling of numeric strings.

        The ] operator uses character-by-character ASCII comparison.
        This test verifies ] with string literals produces correct ASG.
        """
        # Test follows (]) with string literals
        # "AB" follows "AA" in ASCII order
        value = get_expression_from_set('S X="AB"]"AA"')

        assert isinstance(value, MBinaryOp)
        assert value.operator == "]"
        assert isinstance(value.left, StringLiteral)
        assert isinstance(value.right, StringLiteral)
        assert value.left.value == "AB"
        assert value.right.value == "AA"

        # Test with lowercase - "a" follows "Z" (lowercase > uppercase in ASCII)
        value2 = get_expression_from_set('S X="a"]"Z"')

        assert isinstance(value2, MBinaryOp)
        assert value2.operator == "]"
        assert value2.left.value == "a"
        assert value2.right.value == "Z"
