"""Tests for ZPRINT command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for ZPRINT command tests."""
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
class TestZprintParsing:
    """Parser-level tests for ZPRINT command (YDB)."""

    def test_zprint_simple(self, command_metamodel):
        """ZPRINT label - print from label."""
        model = command_metamodel.model_from_str("ZPRINT label", "ZPrintCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zprint_abbreviated(self, command_metamodel):
        """ZP label - abbreviated."""
        model = command_metamodel.model_from_str("ZP label", "ZPrintCommand")
        assert len(model.args) == 1

    def test_zprint_label_routine(self, command_metamodel):
        """ZPRINT label^routine."""
        model = command_metamodel.model_from_str(
            "ZPRINT label^routine", "ZPrintCommand"
        )
        assert len(model.args) == 1

    def test_zprint_no_args(self, command_metamodel):
        """ZPRINT - print current routine."""
        model = command_metamodel.model_from_str("ZPRINT", "ZPrintCommand")
        assert len(model.args) == 0
