"""Tests for ZGOTO command parsing (YDB extension).

Reference: YottaDB Z-Commands
Migrated from: tests/unit/test_command_grammar.py
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZGotoCommand:
    """Tests for ZGOTO command parsing."""

    def test_zgoto_level(self, command_metamodel):
        """ZGOTO 1 - unwind to level 1"""
        model = command_metamodel.model_from_str("ZGOTO 1", "ZGotoCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zgoto_abbreviated(self, command_metamodel):
        """ZGO 0 - abbreviated"""
        model = command_metamodel.model_from_str("ZGO 0", "ZGotoCommand")
        assert len(model.args) == 1

    def test_zgoto_level_target(self, command_metamodel):
        """ZGOTO 1:label^routine - unwind and goto"""
        model = command_metamodel.model_from_str(
            "ZGOTO 1:label^routine", "ZGotoCommand"
        )
        assert len(model.args) == 1
        assert model.args[0].target is not None

    def test_zgoto_zlevel(self, command_metamodel):
        """ZGOTO $ZLEVEL:label - use $ZLEVEL"""
        model = command_metamodel.model_from_str("ZGOTO $ZLEVEL:label", "ZGotoCommand")
        assert len(model.args) == 1

    def test_zgoto_no_args(self, command_metamodel):
        """ZGOTO - return to direct mode"""
        model = command_metamodel.model_from_str("ZGOTO", "ZGotoCommand")
        assert len(model.args) == 0
