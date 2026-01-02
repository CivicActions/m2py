"""Tests for ZMESSAGE command parsing (YDB extension).

Reference: YottaDB Z-Commands
Migrated from: tests/unit/test_command_grammar.py
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZMessageCommand:
    """Tests for ZMESSAGE command parsing."""

    def test_zmessage_simple(self, command_metamodel):
        """ZMESSAGE 150372994 - generate error"""
        model = command_metamodel.model_from_str(
            "ZMESSAGE 150372994", "ZMessageCommand"
        )
        assert model is not None
        assert len(model.args) == 1

    def test_zmessage_abbreviated(self, command_metamodel):
        """ZM err - abbreviated"""
        model = command_metamodel.model_from_str("ZM err", "ZMessageCommand")
        assert len(model.args) == 1
