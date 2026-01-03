"""Tests for Variable Names parsing (§7.1.2).

Tests verify the textX grammar correctly captures variable name syntax
including local variables (lvn), global variables (gvn), and general variables (glvn).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.2
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_expression_classes


@pytest.fixture(scope="module")
def expr_metamodel():
    """Load the expression grammar metamodel with custom classes."""
    grammar_path = (
        Path(__file__).parent.parent.parent.parent.parent
        / "src"
        / "m2py"
        / "grammar"
        / "expressions.tx"
    )
    return metamodel_from_file(
        str(grammar_path), classes=get_expression_classes(), skipws=True
    )


@pytest.mark.parser
class TestLocalVariables:
    """Test local variable parsing (§7.1.2)."""

    def test_local_variable_simple(self, expr_metamodel):
        """Simple local variable X parses correctly (§7.1.2)."""
        model = expr_metamodel.model_from_str("X", "Expr")
        assert model is not None

    def test_percent_variable(self, expr_metamodel):
        """%-prefixed variable parses correctly (§7.1.2)."""
        model = expr_metamodel.model_from_str("%ABC", "Expr")
        assert model is not None

    def test_local_variable_subscripted(self, expr_metamodel):
        """Subscripted local variable DATA(1,2,3) parses correctly (§7.1.2)."""
        model = expr_metamodel.model_from_str("DATA(1,2,3)", "Expr")
        assert model is not None


@pytest.mark.parser
class TestGlobalVariables:
    """Test global variable parsing (§7.1.2)."""

    def test_global_variable_simple(self, expr_metamodel):
        """Simple global variable ^GLOBAL parses correctly (§7.1.2)."""
        model = expr_metamodel.model_from_str("^GLOBAL", "Expr")
        assert model is not None

    def test_global_variable_subscripted(self, expr_metamodel):
        """Subscripted global variable ^DATA(1,2) parses correctly (§7.1.2)."""
        model = expr_metamodel.model_from_str("^DATA(1,2)", "Expr")
        assert model is not None

    def test_naked_global_reference(self, expr_metamodel):
        """Naked global reference ^(1,2) parses correctly (§7.1.2)."""
        model = expr_metamodel.model_from_str("^(1,2)", "Expr")
        assert model is not None


@pytest.mark.parser
class TestExtendedGlobalReferences:
    """Test extended global reference parsing (§7.1.2).

    Extended global references allow specifying an environment or global
    directory for the global variable, enabling cross-environment access.
    """

    def test_pipe_extended_global(self, expr_metamodel):
        """Parse pipe-delimited extended global: ^|\"env\"|name (§7.1.2)."""
        model = expr_metamodel.model_from_str('^|"env"|global', "Expr")
        assert model is not None

    def test_pipe_extended_global_subscripted(self, expr_metamodel):
        """Parse pipe-delimited extended global with subscripts (§7.1.2)."""
        model = expr_metamodel.model_from_str('^|"db"|data(1,2)', "Expr")
        assert model is not None

    def test_bracket_extended_global(self, expr_metamodel):
        """Parse bracket-delimited extended global: ^[\"gld\"]name (§7.1.2)."""
        model = expr_metamodel.model_from_str('^["mumps.gld"]global', "Expr")
        assert model is not None

    def test_bracket_extended_global_subscripted(self, expr_metamodel):
        """Parse bracket-delimited extended global with subscripts (§7.1.2)."""
        model = expr_metamodel.model_from_str('^["gld"]data(1,2,3)', "Expr")
        assert model is not None

    def test_extended_global_reference(self, expr_metamodel):
        """Extended global reference ^|""|global parses correctly (§7.1.2)."""
        model = expr_metamodel.model_from_str('^|""|global', "Expr")
        assert model is not None
