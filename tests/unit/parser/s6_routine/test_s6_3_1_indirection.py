"""Tests for Generic Indirection parsing (§6.3.1).

Tests verify the textX grammar correctly captures indirection syntax.

Reference: MUMPS 1995 ANSI Standard, Section 6.3.1
"""

import pytest

from m2py.asg import IndirectionType
from m2py.parser.textx_classes import Indirection


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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: subscript indirection")
    def test_subscript_indirection(self, parse_line):
        """Subscript indirection @var@(sub) parses correctly (§6.3.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: argument indirection")
    def test_argument_indirection(self, parse_line):
        """Argument indirection @(expr) parses correctly (§6.3.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: pattern indirection")
    def test_pattern_indirection(self, parse_line):
        """Pattern indirection X?@pattern parses correctly (§6.3.1)."""
        pytest.fail("Stub - implement test")
