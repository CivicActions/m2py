"""Tests for ZMESSAGE command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for ZMESSAGE command tests."""
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
class TestZmessageParsing:
    """Parser-level tests for ZMESSAGE command (YDB)."""

    def test_zmessage_simple(self, command_metamodel):
        """ZMESSAGE 150372994 - generate error."""
        model = command_metamodel.model_from_str(
            "ZMESSAGE 150372994", "ZMessageCommand"
        )
        assert model is not None
        assert len(model.args) == 1

    def test_zmessage_abbreviated(self, command_metamodel):
        """ZM err - abbreviated."""
        model = command_metamodel.model_from_str("ZM err", "ZMessageCommand")
        assert len(model.args) == 1
