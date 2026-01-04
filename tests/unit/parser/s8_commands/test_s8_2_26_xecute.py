"""Tests for XECUTE command parsing (§8.2.26).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.26
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for XECUTE command tests."""
    grammar_dir = (
        Path(__file__).parent.parent.parent.parent.parent / "src" / "m2py" / "grammar"
    )
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


@pytest.mark.parser
class TestXecuteCommandParsing:
    """Parser-level tests for XECUTE command (§8.2.26)."""

    def test_xecute_string(self, command_metamodel):
        """X "S X=1" parses correctly (§8.2.26)."""
        model = command_metamodel.model_from_str('X "S X=1"', "XecuteCommand")
        assert len(model.args) == 1

    def test_xecute_expression(self, parse_mumps):
        """XECUTE expr parses correctly (§8.2.26).

        XECUTE can take a variable containing code.
        """
        from m2py.asg import MXecuteStatement

        result = parse_mumps("TEST\n X CMD\n Q")
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        assert isinstance(stmt, MXecuteStatement)
        assert len(stmt.code_expressions) == 1
        assert stmt.is_constant is False

    def test_xecute_with_postcondition(self, parse_mumps):
        """XECUTE:condition expr parses correctly (§8.2.26).

        Postcondition controls whether XECUTE runs.
        """
        from m2py.asg import MXecuteStatement

        result = parse_mumps('TEST\n X:X=1 "S Y=2"\n Q')
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        assert isinstance(stmt, MXecuteStatement)
        assert stmt.postcondition is not None

    def test_xecute_multiple(self, parse_mumps):
        """XECUTE expr1,expr2 multiple expressions parses correctly (§8.2.26).

        Multiple code strings can be executed.
        """
        from m2py.asg import MXecuteStatement

        result = parse_mumps('TEST\n X "S A=1","S B=2"\n Q')
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        assert isinstance(stmt, MXecuteStatement)
        assert len(stmt.code_expressions) == 2

    def test_xecute_abbreviated(self, parse_mumps):
        """X abbreviation parses correctly (§8.2.26).

        X is the standard abbreviation for XECUTE.
        """
        from m2py.asg import MXecuteStatement

        result = parse_mumps('TEST\n X "S X=1"\n Q')
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        assert isinstance(stmt, MXecuteStatement)
