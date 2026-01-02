"""Tests for ZTRIGGER command parsing (YDB extension).

Reference: YottaDB Z-Commands
Migrated from: tests/unit/test_command_grammar.py
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZTriggerCommand:
    """Tests for ZTRIGGER command parsing (Phase 102 Part D)."""

    def test_ztrigger_simple_global(self, command_metamodel):
        """ZTRIGGER ^global - trigger update notification for global"""
        model = command_metamodel.model_from_str("ZTRIGGER ^global", "ZTriggerCommand")
        assert model is not None
        assert len(model.targets) == 1
        # target is Expr -> left (UnaryExpr) -> operand (GlobalVariable)
        global_var = model.targets[0].left.operand
        assert global_var.name == "global"

    def test_ztrigger_subscripted_global(self, command_metamodel):
        """ZTRIGGER ^global(sub) - trigger with subscripted global"""
        model = command_metamodel.model_from_str(
            "ZTRIGGER ^global(sub)", "ZTriggerCommand"
        )
        assert model is not None
        global_var = model.targets[0].left.operand
        assert global_var.name == "global"
        assert len(global_var.subscripts) == 1

    def test_ztrigger_indirection(self, command_metamodel):
        """ZTRIGGER @gbl - trigger with indirection"""
        model = command_metamodel.model_from_str("ZTRIGGER @gbl", "ZTriggerCommand")
        assert model is not None
        assert len(model.targets) == 1

    def test_ztrigger_lowercase(self, command_metamodel):
        """ztrigger ^a - lowercase version"""
        model = command_metamodel.model_from_str("ztrigger ^a", "ZTriggerCommand")
        assert model is not None
        global_var = model.targets[0].left.operand
        assert global_var.name == "a"

    def test_ztrigger_with_postcondition(self, command_metamodel):
        """ZTRIGGER:cond ^a - with postcondition"""
        model = command_metamodel.model_from_str("ZTRIGGER:x ^a", "ZTriggerCommand")
        assert model is not None
        assert model.postcond is not None

    def test_ztrigger_empty_string_subscript(self, command_metamodel):
        """ZTRIGGER ^a("") - with empty string subscript (from test suite)"""
        model = command_metamodel.model_from_str('ZTRIGGER ^a("")', "ZTriggerCommand")
        assert model is not None
        global_var = model.targets[0].left.operand
        assert global_var.name == "a"

    def test_ztrigger_multiple_globals(self, command_metamodel):
        """ZTRIGGER ^a,^b - comma-separated globals"""
        model = command_metamodel.model_from_str("ZTRIGGER ^a,^b", "ZTriggerCommand")
        assert model is not None
        assert len(model.targets) == 2
        assert model.targets[0].left.operand.name == "a"
        assert model.targets[1].left.operand.name == "b"
