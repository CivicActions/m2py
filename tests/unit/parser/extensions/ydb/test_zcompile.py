"""Tests for ZCOMPILE command parsing (YDB extension).

Reference: YottaDB Z-Commands
Migrated from: tests/unit/test_command_grammar.py
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZCompileCommand:
    """Tests for ZCOMPILE command parsing."""

    def test_zcompile_simple(self, command_metamodel):
        """ZCOMPILE routine - compile routine"""
        model = command_metamodel.model_from_str("ZCOMPILE routine", "ZCompileCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zcompile_abbreviated(self, command_metamodel):
        """ZC routine - abbreviated (but note conflict with ZCONTINUE)"""
        # ZC with args should be ZCOMPILE
        model = command_metamodel.model_from_str("ZC routine", "ZCompileCommand")
        assert len(model.args) == 1
