"""Tests for ZCONTINUE command parsing (YDB extension).

Reference: YottaDB Z-Commands
Migrated from: tests/unit/test_command_grammar.py
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZContinueCommand:
    """Tests for ZCONTINUE command parsing."""

    def test_zcontinue_simple(self, command_metamodel):
        """ZCONTINUE - continue from breakpoint"""
        model = command_metamodel.model_from_str("ZCONTINUE", "ZContinueCommand")
        assert model is not None

    def test_zcontinue_lowercase(self, command_metamodel):
        """zcontinue - lowercase"""
        model = command_metamodel.model_from_str("zcontinue", "ZContinueCommand")
        assert model is not None
