"""Tests for ZSTEP command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for ZSTEP command tests."""
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
class TestZstepParsing:
    """Parser-level tests for ZSTEP command (YDB)."""

    def test_zstep_into(self, command_metamodel):
        """ZSTEP INTO - step into subroutines."""
        model = command_metamodel.model_from_str("ZSTEP INTO", "ZStepCommand")
        assert model is not None
        assert model.mode == "INTO"

    def test_zstep_over(self, command_metamodel):
        """ZSTEP OVER - step over subroutines."""
        model = command_metamodel.model_from_str("ZSTEP OVER", "ZStepCommand")
        assert model.mode == "OVER"

    def test_zstep_outof(self, command_metamodel):
        """ZSTEP OUTOF - step out of current routine."""
        model = command_metamodel.model_from_str("ZSTEP OUTOF", "ZStepCommand")
        assert model.mode == "OUTOF"

    def test_zstep_with_action(self, command_metamodel):
        """ZSTEP INTO:"set x=1" - with action expression."""
        model = command_metamodel.model_from_str('ZSTEP INTO:"set x=1"', "ZStepCommand")
        assert model.mode == "INTO"
        assert model.action is not None
