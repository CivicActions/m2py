"""Tests for ZSYSTEM command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for ZSYSTEM command tests."""
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
class TestZsystemParsing:
    """Parser-level tests for ZSYSTEM command (YDB)."""

    def test_zsystem_simple(self, command_metamodel):
        """ZSYSTEM "ls -la" - execute shell command."""
        model = command_metamodel.model_from_str('ZSYSTEM "ls -la"', "ZSystemCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zsystem_abbreviated(self, command_metamodel):
        """ZSY "ls" - abbreviated."""
        model = command_metamodel.model_from_str('ZSY "ls"', "ZSystemCommand")
        assert len(model.args) == 1

    def test_zsystem_variable(self, command_metamodel):
        """ZSYSTEM cmd - variable argument."""
        model = command_metamodel.model_from_str("ZSYSTEM cmd", "ZSystemCommand")
        assert len(model.args) == 1

    def test_zsystem_no_args(self, command_metamodel):
        """ZSYSTEM - spawn interactive shell."""
        model = command_metamodel.model_from_str("ZSYSTEM", "ZSystemCommand")
        assert len(model.args) == 0
