"""Tests for ZCOMPILE command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for ZCOMPILE command tests."""
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
class TestZcompileParsing:
    """Parser-level tests for ZCOMPILE command (YDB)."""

    def test_zcompile_simple(self, command_metamodel):
        """ZCOMPILE routine - compile routine."""
        model = command_metamodel.model_from_str("ZCOMPILE routine", "ZCompileCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zcompile_abbreviated(self, command_metamodel):
        """ZC routine - abbreviated (but note conflict with ZCONTINUE)."""
        model = command_metamodel.model_from_str("ZC routine", "ZCompileCommand")
        assert len(model.args) == 1
