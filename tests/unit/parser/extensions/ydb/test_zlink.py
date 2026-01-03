"""Tests for ZLINK and ZLOAD command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for ZLINK/ZLOAD command tests."""
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
class TestZlinkParsing:
    """Parser-level tests for ZLINK command (YDB)."""

    def test_zlink_simple(self, command_metamodel):
        """ZLINK routine - link routine."""
        model = command_metamodel.model_from_str("ZLINK routine", "ZLinkCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zlink_abbreviated(self, command_metamodel):
        """ZLI routine - abbreviated."""
        model = command_metamodel.model_from_str("ZLI routine", "ZLinkCommand")
        assert len(model.args) == 1

    def test_zlink_string(self, command_metamodel):
        """ZLINK "routine" - string routine name."""
        model = command_metamodel.model_from_str('ZLINK "routine"', "ZLinkCommand")
        assert len(model.args) == 1

    def test_zlink_postcondition(self, command_metamodel):
        """ZLINK:X=1 routine - with postcondition."""
        model = command_metamodel.model_from_str("ZLINK:X=1 routine", "ZLinkCommand")
        assert model.postcond is not None


@pytest.mark.parser
@pytest.mark.ydb
class TestZloadParsing:
    """Parser-level tests for ZLOAD command (YDB)."""

    def test_zload_simple(self, command_metamodel):
        """ZLOAD "file.m" - load source file."""
        model = command_metamodel.model_from_str('ZLOAD "file.m"', "ZLoadCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zload_abbreviated(self, command_metamodel):
        """ZL "file" - abbreviated."""
        model = command_metamodel.model_from_str('ZL "file"', "ZLoadCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zload_no_args(self, command_metamodel):
        """ZLOAD - no argument."""
        model = command_metamodel.model_from_str("ZLOAD", "ZLoadCommand")
        assert model is not None
        assert len(model.args) == 0
