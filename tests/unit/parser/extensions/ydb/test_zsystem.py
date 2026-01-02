"""Tests for ZSYSTEM command parsing (YDB extension).

Reference: YottaDB Z-Commands
Migrated from: tests/unit/test_command_grammar.py
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZSystemCommand:
    """Tests for ZSYSTEM command parsing."""

    def test_zsystem_simple(self, command_metamodel):
        """ZSYSTEM "ls -la" - execute shell command"""
        model = command_metamodel.model_from_str('ZSYSTEM "ls -la"', "ZSystemCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zsystem_abbreviated(self, command_metamodel):
        """ZSY "ls" - abbreviated"""
        model = command_metamodel.model_from_str('ZSY "ls"', "ZSystemCommand")
        assert len(model.args) == 1

    def test_zsystem_variable(self, command_metamodel):
        """ZSYSTEM cmd - variable argument"""
        model = command_metamodel.model_from_str("ZSYSTEM cmd", "ZSystemCommand")
        assert len(model.args) == 1

    def test_zsystem_no_args(self, command_metamodel):
        """ZSYSTEM - spawn interactive shell"""
        model = command_metamodel.model_from_str("ZSYSTEM", "ZSystemCommand")
        assert len(model.args) == 0
