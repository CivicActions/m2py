"""Tests for Generic Indirection parsing (§6.3.1).

Tests verify the textX grammar correctly captures indirection syntax.

Note: Many indirection tests are in asg/s6_routine/test_s6_3_1_indirection.py
which tests both parsing and analysis together. This file contains only
parser-specific tests for unique aspects not covered there.

Reference: MUMPS 1995 ANSI Standard, Section 6.3.1
"""

import pytest

from m2py.parser.textx_classes import Indirection, StringLiteral


@pytest.mark.parser
class TestGenericIndirectionParsing:
    """Parser-level tests for Generic Indirection (§6.3.1).

    The @ operator provides indirection - runtime evaluation of names.

    Note: Name indirection, subscript indirection, and pattern indirection
    are tested in asg/s6_routine/test_s6_3_1_indirection.py with additional
    ASG-level assertions. This class tests parser-specific scenarios.
    """

    def test_argument_indirection_string_literal(self, parse_line):
        """Argument indirection @("literal") parses with string expression (§6.3.1).

        When a string literal is used in indirection, the expression
        attribute should be a StringLiteral. This is unique to the parser
        layer - ASG tests use variable references.
        """
        result = parse_line(' S @("X")=1')
        assert result is not None
        set_stmt = result.labels[0].body.statements[0]
        target = set_stmt.assignments[0].target
        assert isinstance(target, Indirection)
        # The expression is stored in the expression attribute
        assert hasattr(target, "expression")
        assert isinstance(target.expression, StringLiteral)
