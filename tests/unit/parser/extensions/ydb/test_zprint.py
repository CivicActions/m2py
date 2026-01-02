"""Tests for ZPRINT command parsing (YDB extension).

Reference: YottaDB Z-Commands
Migrated from: tests/unit/test_command_grammar.py
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZPrintCommand:
    """Tests for ZPRINT command parsing."""

    def test_zprint_simple(self, command_metamodel):
        """ZPRINT label - print from label"""
        model = command_metamodel.model_from_str("ZPRINT label", "ZPrintCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zprint_abbreviated(self, command_metamodel):
        """ZP label - abbreviated"""
        model = command_metamodel.model_from_str("ZP label", "ZPrintCommand")
        assert len(model.args) == 1

    def test_zprint_label_routine(self, command_metamodel):
        """ZPRINT label^routine"""
        model = command_metamodel.model_from_str(
            "ZPRINT label^routine", "ZPrintCommand"
        )
        assert len(model.args) == 1

    def test_zprint_no_args(self, command_metamodel):
        """ZPRINT - print current routine"""
        model = command_metamodel.model_from_str("ZPRINT", "ZPrintCommand")
        assert len(model.args) == 0
