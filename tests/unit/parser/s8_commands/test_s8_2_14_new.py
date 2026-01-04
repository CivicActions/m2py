"""Tests for NEW command parsing (§8.2.14).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.14
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for NEW command tests."""
    grammar_dir = (
        Path(__file__).parent.parent.parent.parent.parent / "src" / "m2py" / "grammar"
    )
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


@pytest.mark.parser
class TestNewCommandParsing:
    """Parser-level tests for NEW command (§8.2.14)."""

    def test_new_single_variable(self, command_metamodel):
        """N X parses correctly (§8.2.14)."""
        model = command_metamodel.model_from_str("N X", "NewCommand")
        assert len(model.vars) == 1

    def test_new_multiple_variables(self, command_metamodel):
        """N X,Y,Z multiple variables parses correctly (§8.2.14)."""
        model = command_metamodel.model_from_str("N X,Y,Z", "NewCommand")
        assert len(model.vars) == 3

    def test_new_exclusive(self, command_metamodel):
        """N (X) exclusive NEW parses correctly (§8.2.14)."""
        model = command_metamodel.model_from_str("N (X)", "NewCommand")
        assert model.exclusive is not None

    def test_new_argumentless(self, parse_mumps):
        """NEW without argument parses correctly (§8.2.14).

        Argumentless NEW saves all local variables for later restoration.
        """
        from m2py.asg import MNewStatement

        result = parse_mumps("TEST\n N\n Q")
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        assert isinstance(stmt, MNewStatement)
        # Argumentless NEW has empty variables list
        assert stmt.variables == []
        assert stmt.exclusive is False

    def test_new_abbreviated(self, parse_mumps):
        """N abbreviation parses correctly (§8.2.14).

        N is the standard abbreviation for NEW.
        """
        from m2py.asg import MNewStatement

        result = parse_mumps("TEST\n N X,Y\n Q")
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        assert isinstance(stmt, MNewStatement)
        assert len(stmt.variables) == 2
