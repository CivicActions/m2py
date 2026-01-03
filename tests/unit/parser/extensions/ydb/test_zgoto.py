"""Tests for ZGOTO command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for ZGOTO command tests."""
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
class TestZgotoParsing:
    """Parser-level tests for ZGOTO command (YDB)."""

    def test_zgoto_level(self, command_metamodel):
        """ZGOTO 1 - unwind to level 1."""
        model = command_metamodel.model_from_str("ZGOTO 1", "ZGotoCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zgoto_abbreviated(self, command_metamodel):
        """ZGO 0 - abbreviated."""
        model = command_metamodel.model_from_str("ZGO 0", "ZGotoCommand")
        assert len(model.args) == 1

    def test_zgoto_level_target(self, command_metamodel):
        """ZGOTO 1:label^routine - unwind and goto."""
        model = command_metamodel.model_from_str(
            "ZGOTO 1:label^routine", "ZGotoCommand"
        )
        assert len(model.args) == 1
        assert model.args[0].target is not None

    def test_zgoto_zlevel(self, command_metamodel):
        """ZGOTO $ZLEVEL:label - use $ZLEVEL."""
        model = command_metamodel.model_from_str("ZGOTO $ZLEVEL:label", "ZGotoCommand")
        assert len(model.args) == 1

    def test_zgoto_no_args(self, command_metamodel):
        """ZGOTO - return to direct mode."""
        model = command_metamodel.model_from_str("ZGOTO", "ZGotoCommand")
        assert len(model.args) == 0
