"""Tests for ZKILL/ZWITHDRAW command parsing (YDB extension).

Reference: YottaDB Z-Commands
Migrated from: tests/unit/test_command_grammar.py
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZKillCommand:
    """Tests for ZKILL command parsing."""

    def test_zkill_simple(self, command_metamodel):
        """ZKILL X - zkill variable"""
        model = command_metamodel.model_from_str("ZKILL X", "ZKillCommand")
        assert model is not None
        assert len(model.targets) == 1

    def test_zkill_abbreviated(self, command_metamodel):
        """ZKI X - abbreviated"""
        model = command_metamodel.model_from_str("ZKI X", "ZKillCommand")
        assert len(model.targets) == 1

    def test_zkill_subscripted(self, command_metamodel):
        """ZKILL X(1) - zkill subscripted variable"""
        model = command_metamodel.model_from_str("ZKILL X(1)", "ZKillCommand")
        assert len(model.targets) == 1


@pytest.mark.parser
@pytest.mark.ydb
class TestZWithdrawCommand:
    """Tests for ZWITHDRAW command parsing."""

    def test_zwithdraw_simple(self, command_metamodel):
        """ZWITHDRAW X - zwithdraw variable"""
        model = command_metamodel.model_from_str("ZWITHDRAW X", "ZWithdrawCommand")
        assert model is not None
        assert len(model.targets) == 1

    def test_zwithdraw_abbreviated(self, command_metamodel):
        """ZWI X - abbreviated"""
        model = command_metamodel.model_from_str("ZWI X", "ZWithdrawCommand")
        assert len(model.targets) == 1

    def test_zwithdraw_multiple(self, command_metamodel):
        """zwithdraw ^a(1,2),^b - multiple targets"""
        model = command_metamodel.model_from_str(
            "zwithdraw ^a(1,2),^b", "ZWithdrawCommand"
        )
        assert len(model.targets) == 2

    def test_zwithdraw_global(self, command_metamodel):
        """ZWITHDRAW ^GLOBAL - global variable"""
        model = command_metamodel.model_from_str(
            "ZWITHDRAW ^GLOBAL", "ZWithdrawCommand"
        )
        assert len(model.targets) == 1

    def test_zwithdraw_postcondition(self, command_metamodel):
        """zwithdraw:tf X - with postcondition"""
        model = command_metamodel.model_from_str("zwithdraw:tf X", "ZWithdrawCommand")
        assert model.postcond is not None
