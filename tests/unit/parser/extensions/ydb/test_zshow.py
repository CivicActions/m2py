"""Tests for ZSHOW command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for ZSHOW command tests."""
    grammar_dir = (
        Path(__file__).parent.parent.parent.parent.parent.parent
        / "src"
        / "m2py"
        / "grammar"
    )
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


@pytest.mark.parser
@pytest.mark.ydb
class TestZshowParsing:
    """Parser-level tests for ZSHOW command (YDB)."""

    def test_zshow_simple(self, command_metamodel):
        """ZSHOW "BS" - show breakpoints and stack."""
        model = command_metamodel.model_from_str('ZSHOW "BS"', "ZShowCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zshow_abbreviated(self, command_metamodel):
        """ZSH "V" - abbreviated ZSHOW."""
        model = command_metamodel.model_from_str('ZSH "V"', "ZShowCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zshow_all(self, command_metamodel):
        """ZSHOW "*" - show all."""
        model = command_metamodel.model_from_str('ZSHOW "*"', "ZShowCommand")
        assert len(model.args) == 1

    def test_zshow_with_destination(self, command_metamodel):
        """ZSHOW "V":^RESULT - show variables to global."""
        model = command_metamodel.model_from_str('ZSHOW "V":^RESULT', "ZShowCommand")
        assert len(model.args) == 1
        assert model.args[0].destination is not None

    def test_zshow_no_args(self, command_metamodel):
        """ZSHOW - argumentless."""
        model = command_metamodel.model_from_str("ZSHOW", "ZShowCommand")
        assert len(model.args) == 0

    def test_zshow_postcondition(self, command_metamodel):
        """ZSHOW:X=1 "V" - with postcondition."""
        model = command_metamodel.model_from_str('ZSHOW:X=1 "V"', "ZShowCommand")
        assert model.postcond is not None

    def test_zshow_destination_local(self, command_metamodel):
        """zshow "s":stack - output to local variable."""
        model = command_metamodel.model_from_str('zshow "s":stack', "ZShowCommand")
        assert len(model.args) == 1
        assert model.args[0].destination is not None

    def test_zshow_destination_indirection(self, command_metamodel):
        """ZSHOW "L":@gvar - output with indirection."""
        model = command_metamodel.model_from_str('ZSHOW "L":@gvar', "ZShowCommand")
        assert len(model.args) == 1
        assert model.args[0].destination is not None

    def test_zshow_destination_subscripted_global(self, command_metamodel):
        """ZSHOW "*":^XUTL("XUSYS",$J,"JE") - output to subscripted global."""
        model = command_metamodel.model_from_str(
            'ZSHOW "*":^XUTL("XUSYS",$J,"JE")', "ZShowCommand"
        )
        assert len(model.args) == 1
        assert model.args[0].destination is not None

    def test_zshow_lowercase(self, command_metamodel):
        """zshow "*" - lowercase."""
        model = command_metamodel.model_from_str('zshow "*"', "ZShowCommand")
        assert len(model.args) == 1
