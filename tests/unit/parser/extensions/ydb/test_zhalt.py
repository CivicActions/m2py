"""Tests for ZHALT command parsing (YDB extension).

Reference: YottaDB Z-Commands
Migrated from: tests/unit/test_command_grammar.py
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZHaltCommand:
    """Tests for ZHALT command parsing."""

    def test_zhalt_simple(self, command_metamodel):
        """zhalt 1 - halt with exit code"""
        model = command_metamodel.model_from_str("zhalt 1", "ZHaltCommand")
        assert model is not None
        assert model.exitcode is not None

    def test_zhalt_uppercase(self, command_metamodel):
        """ZHALT 1 - uppercase"""
        model = command_metamodel.model_from_str("ZHALT 1", "ZHaltCommand")
        assert model.exitcode is not None

    def test_zhalt_abbreviated(self, command_metamodel):
        """zh 0 - abbreviated"""
        model = command_metamodel.model_from_str("zh 0", "ZHaltCommand")
        assert model.exitcode is not None

    def test_zhalt_expression(self, command_metamodel):
        """zhalt +$zstatus - with expression"""
        model = command_metamodel.model_from_str("zhalt +$zstatus", "ZHaltCommand")
        assert model.exitcode is not None

    def test_zhalt_postcondition(self, command_metamodel):
        """zhalt:tf 1 - with postcondition"""
        model = command_metamodel.model_from_str("zhalt:tf 1", "ZHaltCommand")
        assert model.postcond is not None
        assert model.exitcode is not None
