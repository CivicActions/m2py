"""Tests for ZALLOCATE/ZDEALLOCATE command parsing (YDB extension).

Reference: YottaDB Z-Commands
Migrated from: tests/unit/test_command_grammar.py
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZAllocateCommand:
    """Tests for ZALLOCATE command parsing."""

    def test_zallocate_simple(self, command_metamodel):
        """za X - simple zallocate"""
        model = command_metamodel.model_from_str("za X", "ZAllocateCommand")
        assert model is not None
        assert len(model.targets) == 1

    def test_zallocate_with_timeout(self, command_metamodel):
        """za X:5 - with timeout"""
        model = command_metamodel.model_from_str("za X:5", "ZAllocateCommand")
        assert len(model.targets) == 1
        assert model.targets[0].timeout is not None

    def test_zallocate_list(self, command_metamodel):
        """Zallocate (@lvar,@gvar):60 - parenthesized list"""
        model = command_metamodel.model_from_str(
            "Zallocate (@lvar,@gvar):60", "ZAllocateCommand"
        )
        assert model.locklist is not None
        assert len(model.locklist.targets) == 2
        assert model.locklist.timeout is not None

    def test_zallocate_postcondition(self, command_metamodel):
        """Zallocate:'(i#2) X - with postcondition"""
        model = command_metamodel.model_from_str(
            "Zallocate:'(i#2) X", "ZAllocateCommand"
        )
        assert model.postcond is not None
        assert len(model.targets) == 1

    def test_zallocate_full(self, command_metamodel):
        """Zallocate:'(i#2) (@lvar,@gvar):60 - full syntax"""
        model = command_metamodel.model_from_str(
            "Zallocate:'(i#2) (@lvar,@gvar):60", "ZAllocateCommand"
        )
        assert model.postcond is not None
        assert model.locklist is not None
        assert len(model.locklist.targets) == 2


@pytest.mark.parser
@pytest.mark.ydb
class TestZDeallocateCommand:
    """Tests for ZDEALLOCATE command parsing."""

    def test_zdeallocate_simple(self, command_metamodel):
        """zd X - simple zdeallocate"""
        model = command_metamodel.model_from_str("zd X", "ZDeallocateCommand")
        assert model is not None
        assert len(model.targets) == 1

    def test_zdeallocate_full_spelling(self, command_metamodel):
        """zdeallocate X - full spelling"""
        model = command_metamodel.model_from_str("zdeallocate X", "ZDeallocateCommand")
        assert len(model.targets) == 1

    def test_zdeallocate_list(self, command_metamodel):
        """Zdeallocate (@lvar,@gvar) - parenthesized list"""
        model = command_metamodel.model_from_str(
            "Zdeallocate (@lvar,@gvar)", "ZDeallocateCommand"
        )
        assert model.locklist is not None
        assert len(model.locklist.targets) == 2

    def test_zdeallocate_postcondition(self, command_metamodel):
        """Zdeallocate:'(i#2) X - with postcondition"""
        model = command_metamodel.model_from_str(
            "Zdeallocate:'(i#2) X", "ZDeallocateCommand"
        )
        assert model.postcond is not None
        assert len(model.targets) == 1

    def test_zdeallocate_full(self, command_metamodel):
        """Zdeallocate:'(i#2) (@lvar,@gvar) - full syntax from longname test"""
        model = command_metamodel.model_from_str(
            "Zdeallocate:'(i#2) (@lvar,@gvar)", "ZDeallocateCommand"
        )
        assert model.postcond is not None
        assert model.locklist is not None
        assert len(model.locklist.targets) == 2

    def test_zdeallocate_multiple_targets(self, command_metamodel):
        """zd ^a,^b - multiple targets"""
        model = command_metamodel.model_from_str("zd ^a,^b", "ZDeallocateCommand")
        assert len(model.targets) == 2

    def test_zdeallocate_global(self, command_metamodel):
        """ZD ^GLOBAL - global variable"""
        model = command_metamodel.model_from_str("ZD ^GLOBAL", "ZDeallocateCommand")
        assert len(model.targets) == 1
