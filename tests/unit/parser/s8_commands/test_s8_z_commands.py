"""Tests for Z-commands parsing (YDB Extensions).

Reference: YDB-specific extensions to MUMPS

Note: Additional comprehensive tests for each Z-command are in
tests/unit/parser/extensions/ydb/ - these tests verify basic parsing
at the routine level using MUMPSParser.
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
class TestZCommandsParsing:
    """Parser-level tests for YDB Z-commands."""

    def test_zcontinue(self, command_metamodel):
        """ZCONTINUE parses correctly (YDB extension)."""
        model = command_metamodel.model_from_str("ZCONTINUE", "ZContinueCommand")
        assert model is not None

    def test_zhalt(self, command_metamodel):
        """ZHALT parses correctly (YDB extension)."""
        model = command_metamodel.model_from_str("ZHALT 0", "ZHaltCommand")
        assert model is not None
        assert model.exitcode is not None

    def test_zwrite(self, command_metamodel):
        """ZWRITE parses correctly (YDB extension)."""
        model = command_metamodel.model_from_str("ZWRITE X", "ZWriteCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zbreak(self, command_metamodel):
        """ZBREAK parses correctly (YDB extension)."""
        model = command_metamodel.model_from_str("ZBREAK label", "ZBreakCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zkill(self, command_metamodel):
        """ZKILL parses correctly (YDB extension)."""
        model = command_metamodel.model_from_str("ZKILL X", "ZKillCommand")
        assert model is not None
        assert len(model.targets) == 1

    def test_zlink(self, command_metamodel):
        """ZLINK parses correctly (YDB extension)."""
        model = command_metamodel.model_from_str("ZLINK routine", "ZLinkCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zmessage(self, command_metamodel):
        """ZMESSAGE parses correctly (YDB extension)."""
        model = command_metamodel.model_from_str(
            "ZMESSAGE 150382298", "ZMessageCommand"
        )
        assert model is not None
        assert len(model.args) == 1

    def test_zprint(self, command_metamodel):
        """ZPRINT parses correctly (YDB extension)."""
        model = command_metamodel.model_from_str("ZPRINT label", "ZPrintCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zshow(self, command_metamodel):
        """ZSHOW parses correctly (YDB extension)."""
        model = command_metamodel.model_from_str("ZSHOW", "ZShowCommand")
        assert model is not None

    def test_zstep(self, command_metamodel):
        """ZSTEP parses correctly (YDB extension)."""
        model = command_metamodel.model_from_str("ZSTEP INTO", "ZStepCommand")
        assert model is not None
        assert model.mode is not None

    def test_zsystem(self, command_metamodel):
        """ZSYSTEM parses correctly (YDB extension)."""
        model = command_metamodel.model_from_str('ZSYSTEM "ls"', "ZSystemCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_ztstart(self, command_metamodel):
        """ZTSTART parses correctly (YDB extension)."""
        model = command_metamodel.model_from_str("ZTSTART", "ZTStartCommand")
        assert model is not None

    def test_ztcommit(self, command_metamodel):
        """ZTCOMMIT parses correctly (YDB extension)."""
        model = command_metamodel.model_from_str("ZTCOMMIT", "ZTCommitCommand")
        assert model is not None
