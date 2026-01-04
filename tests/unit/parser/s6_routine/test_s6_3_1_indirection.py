"""Tests for Generic Indirection parsing (§6.3.1).

Tests verify the textX grammar correctly captures indirection syntax.

Reference: MUMPS 1995 ANSI Standard, Section 6.3.1
"""

import pytest

from m2py.asg import IndirectionType, MIfStatement, MPatternMatch
from m2py.parser.textx_classes import Indirection, StringLiteral


@pytest.mark.parser
class TestGenericIndirectionParsing:
    """Parser-level tests for Generic Indirection (§6.3.1).

    The @ operator provides indirection - runtime evaluation of names.
    """

    def test_name_indirection(self, parse_line):
        """Name indirection @var parses correctly (§6.3.1).

        Name indirection: @VAR evaluates VAR to get a variable name.
        """
        result = parse_line(" S @VAR=1")
        assert result is not None
        # Get the SET statement target
        set_stmt = result.labels[0].body.statements[0]
        target = set_stmt.assignments[0].target
        assert isinstance(target, Indirection)
        assert target.indirection_type == IndirectionType.NAME

    def test_subscript_indirection(self, parse_line):
        """Subscript indirection @var@(sub) parses correctly (§6.3.1).

        Subscript indirection: @VAR@(sub) evaluates VAR to get a variable name,
        then appends the subscripts.
        """
        result = parse_line(" S @X@(1)=Y")
        assert result is not None
        set_stmt = result.labels[0].body.statements[0]
        target = set_stmt.assignments[0].target
        assert isinstance(target, Indirection)
        assert target.indirection_type == IndirectionType.NAME
        # Subscripts are stored in name_indirection_subscripts
        assert target.name_indirection_subscripts is not None
        assert len(target.name_indirection_subscripts) > 0

    def test_argument_indirection(self, parse_line):
        """Argument indirection @(expr) parses correctly (§6.3.1).

        Argument indirection: @(expr) evaluates expr to get a string
        that becomes the variable name.
        """
        result = parse_line(' S @("X")=1')
        assert result is not None
        set_stmt = result.labels[0].body.statements[0]
        target = set_stmt.assignments[0].target
        assert isinstance(target, Indirection)
        # The expression is stored in the expression attribute
        assert hasattr(target, "expression")
        assert isinstance(target.expression, StringLiteral)

    def test_pattern_indirection(self, parse_line):
        """Pattern indirection X?@pattern parses correctly (§6.3.1).

        Pattern indirection: X?@PAT evaluates PAT to get the pattern to match.
        """
        result = parse_line(' I X?@PAT W "match"')
        assert result is not None
        if_stmt = result.labels[0].body.statements[0]
        assert isinstance(if_stmt, MIfStatement)
        # The condition contains a pattern match with indirect pattern
        condition = if_stmt.condition
        assert isinstance(condition, MPatternMatch)
        assert condition.pattern_indirect is not None
