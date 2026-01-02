"""Tests for Variable Names parsing (§7.1.2).

Tests verify the textX grammar correctly captures variable name syntax
including local variables (lvn), global variables (gvn), and general variables (glvn).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.2

Migrated from: tests/unit/test_expression_grammar.py (TestLocalVariables, TestGlobalVariables, TestExtendedGlobalReferences)
"""

import pytest


@pytest.mark.parser
class TestLocalVariables:
    """Test local variable parsing (§7.1.2).

    Migrated from: tests/unit/test_expression_grammar.py::TestLocalVariables
    """

    def test_simple_variable(self, parse_expression):
        """Parse simple variable name (§7.1.2)."""
        model = parse_expression("X")
        assert model is not None

    def test_percent_variable(self, parse_expression):
        """Parse %-prefixed variable (§7.1.2)."""
        model = parse_expression("%ABC")
        assert model is not None

    def test_subscripted_variable(self, parse_expression):
        """Parse subscripted variable (§7.1.2)."""
        model = parse_expression("DATA(1,2,3)")
        assert model is not None


@pytest.mark.parser
class TestGlobalVariables:
    """Test global variable parsing (§7.1.2).

    Migrated from: tests/unit/test_expression_grammar.py::TestGlobalVariables
    """

    def test_simple_global(self, parse_expression):
        """Parse simple global (§7.1.2)."""
        model = parse_expression("^GLOBAL")
        assert model is not None

    def test_subscripted_global(self, parse_expression):
        """Parse subscripted global (§7.1.2)."""
        model = parse_expression("^DATA(1,2)")
        assert model is not None

    def test_naked_global(self, parse_expression):
        """Parse naked global reference (§7.1.2)."""
        model = parse_expression("^(1,2)")
        assert model is not None


@pytest.mark.parser
class TestExtendedGlobalReferences:
    """Test extended global reference parsing (§7.1.2).

    Extended global references: ^|"env"|name and ^["gld"]name.
    Allow specifying an environment or global directory for cross-environment access.

    Migrated from: tests/unit/test_expression_grammar.py::TestExtendedGlobalReferences
    """

    def test_pipe_extended_global(self, parse_expression):
        """Parse pipe-delimited extended global: ^|"env"|name (§7.1.2)."""
        model = parse_expression('^|"env"|global')
        assert model is not None

    def test_pipe_extended_global_subscripted(self, parse_expression):
        """Parse pipe-delimited extended global with subscripts (§7.1.2)."""
        model = parse_expression('^|"db"|data(1,2)')
        assert model is not None

    def test_bracket_extended_global(self, parse_expression):
        """Parse bracket-delimited extended global: ^["gld"]name (§7.1.2)."""
        model = parse_expression('^["mumps.gld"]global')
        assert model is not None

    def test_bracket_extended_global_subscripted(self, parse_expression):
        """Parse bracket-delimited extended global with subscripts (§7.1.2)."""
        model = parse_expression('^["gld"]data(1,2,3)')
        assert model is not None

    def test_pipe_extended_global_empty_env(self, parse_expression):
        """Parse pipe-delimited extended global with empty environment (§7.1.2)."""
        model = parse_expression('^|""|global')
        assert model is not None
