"""Tests for ZWRITE command parsing (YDB extension).

Reference: YottaDB Z-Commands
Migrated from: tests/unit/test_command_grammar.py
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZWriteCommand:
    """Tests for ZWRITE command parsing."""

    def test_zwrite_simple(self, command_metamodel):
        """ZWRITE X - write variable X"""
        model = command_metamodel.model_from_str("ZWRITE X", "ZWriteCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zwrite_abbreviated(self, command_metamodel):
        """ZWR X - abbreviated"""
        model = command_metamodel.model_from_str("ZWR X", "ZWriteCommand")
        assert len(model.args) == 1

    def test_zwrite_global(self, command_metamodel):
        """ZWR ^GLOBAL - write global"""
        model = command_metamodel.model_from_str("ZWR ^GLOBAL", "ZWriteCommand")
        assert len(model.args) == 1

    def test_zwrite_indirection(self, command_metamodel):
        """ZWR @var - write via indirection"""
        model = command_metamodel.model_from_str("ZWR @var", "ZWriteCommand")
        assert len(model.args) == 1

    def test_zwrite_no_args(self, command_metamodel):
        """ZWR - write all locals"""
        model = command_metamodel.model_from_str("ZWR", "ZWriteCommand")
        assert len(model.args) == 0

    def test_zwrite_global_pattern(self, command_metamodel):
        """ZWRITE ^?.E - write globals matching pattern"""
        model = command_metamodel.model_from_str("ZWRITE ^?.E", "ZWriteCommand")
        assert model is not None
        assert len(model.args) == 1
        # The target should be a ZWriteGlobalPattern
        target = model.args[0].target
        assert target.__class__.__name__ == "ZWriteGlobalPattern"

    def test_zwrite_global_pattern_complex(self, command_metamodel):
        """ZWRITE ^?1"%"2U.E - complex pattern"""
        model = command_metamodel.model_from_str('ZWRITE ^?1"%"2U.E', "ZWriteCommand")
        assert model is not None
        assert len(model.args) == 1


@pytest.mark.parser
@pytest.mark.ydb
class TestZWriteArgumentless:
    """Tests for argumentless ZWRITE followed by other commands.

    Migrated from: tests/unit/test_command_grammar.py
    """

    def test_zwrite_argumentless(self, command_metamodel):
        """ZWRITE - no arguments (shows all locals)"""
        model = command_metamodel.model_from_str("ZWRITE", "ZWriteCommand")
        assert len(model.args) == 0

    def test_zwrite_with_args(self, command_metamodel):
        """ZWRITE x - with variable argument"""
        model = command_metamodel.model_from_str("ZWRITE x", "ZWriteCommand")
        assert len(model.args) == 1
