"""Tests for ZSTEP command parsing (YDB extension).

Reference: YottaDB Z-Commands
Migrated from: tests/unit/test_command_grammar.py
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZStepCommand:
    """Tests for ZSTEP command parsing (Phase 103)."""

    def test_zstep_into(self, command_metamodel):
        """ZSTEP INTO - step into subroutines"""
        model = command_metamodel.model_from_str("ZSTEP INTO", "ZStepCommand")
        assert model is not None
        assert model.mode == "INTO"

    def test_zstep_over(self, command_metamodel):
        """ZSTEP OVER - step over subroutines"""
        model = command_metamodel.model_from_str("ZSTEP OVER", "ZStepCommand")
        assert model.mode == "OVER"

    def test_zstep_outof(self, command_metamodel):
        """ZSTEP OUTOF - step out of current routine"""
        model = command_metamodel.model_from_str("ZSTEP OUTOF", "ZStepCommand")
        assert model.mode == "OUTOF"

    def test_zstep_with_action(self, command_metamodel):
        """ZSTEP INTO:"set x=1" - with action expression"""
        model = command_metamodel.model_from_str('ZSTEP INTO:"set x=1"', "ZStepCommand")
        assert model.mode == "INTO"
        assert model.action is not None
