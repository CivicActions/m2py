"""Tests for Expression Values parsing (§7.1.1).

Tests verify the textX grammar correctly captures expression value syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.1.1
"""

import pytest


@pytest.mark.parser
class TestValuesParsing:
    """Parser-level tests for Expression Values (§7.1.1).

    Values are the basic units of expressions: literals, variables, functions.
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: numeric value parsing")
    def test_numeric_value(self, parse_expression):
        """Numeric value parses correctly (§7.1.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: string value parsing")
    def test_string_value(self, parse_expression):
        """String value parses correctly (§7.1.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: variable as value")
    def test_variable_as_value(self, parse_expression):
        """Variable reference as value parses correctly (§7.1.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: function as value")
    def test_function_as_value(self, parse_expression):
        """Function call as value parses correctly (§7.1.1)."""
        pytest.fail("Stub - implement test")
