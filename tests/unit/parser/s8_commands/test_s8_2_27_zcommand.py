"""Tests for Z-command parsing (§8.2.27).

Z-commands are implementation-defined extensions to standard MUMPS.
Reference: MUMPS 1995 ANSI Standard, Section 8.2.27
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for Z-command tests."""
    grammar_dir = (
        Path(__file__).parent.parent.parent.parent.parent / "src" / "m2py" / "grammar"
    )
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


@pytest.mark.parser
@pytest.mark.ydb
class TestZCommandParsing:
    """Parser-level tests for Z-command syntax (§8.2.27)."""

    def test_zcommand_generic(self, command_metamodel):
        """Z-command basic form parses correctly (§8.2.27).

        Per §8.2.27, the Z-command is implementation-defined.
        YDB implements specific Z-commands like ZWRITE, ZBREAK, etc.
        """
        model = command_metamodel.model_from_str("ZWRITE", "ZWriteCommand")
        assert model is not None

    def test_zcommand_with_arguments(self, command_metamodel):
        """Z-command with arguments parses correctly (§8.2.27)."""
        model = command_metamodel.model_from_str("ZWRITE X,Y,Z", "ZWriteCommand")
        assert model is not None
        assert len(model.args) == 3

    def test_zcommand_with_postcondition(self, command_metamodel):
        """Z-command with postcondition parses correctly (§8.2.27)."""
        model = command_metamodel.model_from_str("ZWRITE:tf X", "ZWriteCommand")
        assert model is not None
        assert model.postcond is not None
