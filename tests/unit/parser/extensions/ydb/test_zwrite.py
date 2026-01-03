"""Tests for ZWRITE command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for ZWRITE command tests."""
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
class TestZwriteParsing:
    """Parser-level tests for ZWRITE command (YDB)."""

    def test_zwrite_simple(self, command_metamodel):
        """ZWRITE X - write variable X."""
        model = command_metamodel.model_from_str("ZWRITE X", "ZWriteCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zwrite_abbreviated(self, command_metamodel):
        """ZWR X - abbreviated."""
        model = command_metamodel.model_from_str("ZWR X", "ZWriteCommand")
        assert len(model.args) == 1

    def test_zwrite_global(self, command_metamodel):
        """ZWR ^GLOBAL - write global."""
        model = command_metamodel.model_from_str("ZWR ^GLOBAL", "ZWriteCommand")
        assert len(model.args) == 1

    def test_zwrite_indirection(self, command_metamodel):
        """ZWR @var - write via indirection."""
        model = command_metamodel.model_from_str("ZWR @var", "ZWriteCommand")
        assert len(model.args) == 1

    def test_zwrite_no_args(self, command_metamodel):
        """ZWR - write all locals."""
        model = command_metamodel.model_from_str("ZWR", "ZWriteCommand")
        assert len(model.args) == 0

    def test_zwrite_global_pattern(self, command_metamodel):
        """ZWRITE ^?.E - write globals matching pattern."""
        model = command_metamodel.model_from_str("ZWRITE ^?.E", "ZWriteCommand")
        assert model is not None
        assert len(model.args) == 1
        # The target should be a ZWriteGlobalPattern
        target = model.args[0].target
        assert target.__class__.__name__ == "ZWriteGlobalPattern"

    def test_zwrite_global_pattern_complex(self, command_metamodel):
        """ZWRITE ^?1"%"2U.E - complex pattern."""
        model = command_metamodel.model_from_str('ZWRITE ^?1"%"2U.E', "ZWriteCommand")
        assert model is not None
        assert len(model.args) == 1
