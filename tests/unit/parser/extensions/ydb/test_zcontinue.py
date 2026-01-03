"""Tests for ZCONTINUE command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for ZCONTINUE command tests."""
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
class TestZcontinueParsing:
    """Parser-level tests for ZCONTINUE command (YDB)."""

    def test_zcontinue_simple(self, command_metamodel):
        """ZCONTINUE - continue from breakpoint."""
        model = command_metamodel.model_from_str("ZCONTINUE", "ZContinueCommand")
        assert model is not None

    def test_zcontinue_lowercase(self, command_metamodel):
        """zcontinue - lowercase."""
        model = command_metamodel.model_from_str("zcontinue", "ZContinueCommand")
        assert model is not None
