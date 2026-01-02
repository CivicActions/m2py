"""Tests for Variable Names parsing (§7.1.2).

Tests verify the textX grammar correctly captures variable name syntax
including local variables (lvn), global variables (gvn), and general variables (glvn).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.2
"""

import pytest


@pytest.mark.parser
class TestVariablesParsing:
    """Parser-level tests for Variable Names (§7.1.2).

    Variable types:
    - lvn (local variable name): X, NAME, arr(1,2)
    - gvn (global variable name): ^GLOBAL, ^DATA(key)
    - glvn (general variable name): either lvn or gvn
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: simple local variable")
    def test_local_variable_simple(self, parse_expression):
        """Simple local variable X parses correctly (§7.1.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: local variable with subscripts")
    def test_local_variable_subscripted(self, parse_expression):
        """Subscripted local variable arr(1,2) parses correctly (§7.1.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: simple global variable")
    def test_global_variable_simple(self, parse_expression):
        """Simple global variable ^GLOBAL parses correctly (§7.1.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: global variable with subscripts")
    def test_global_variable_subscripted(self, parse_expression):
        """Subscripted global variable ^DATA(key) parses correctly (§7.1.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: naked global reference")
    def test_naked_global_reference(self, parse_expression):
        """Naked global reference ^(sub) parses correctly (§7.1.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: extended global reference")
    def test_extended_global_reference(self, parse_expression):
        """Extended global reference ^|env|GLOBAL parses correctly (§7.1.2)."""
        pytest.fail("Stub - implement test")
