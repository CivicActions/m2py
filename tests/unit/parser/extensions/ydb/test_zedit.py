"""Tests for ZEDIT command parsing (YDB extension).

Reference: YottaDB Z-Commands
Migrated from: tests/unit/test_command_grammar.py
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZEditCommand:
    """Tests for ZEDIT command parsing (Phase 103)."""

    def test_zedit_routine(self, command_metamodel):
        """ZEDIT routine - edit a routine"""
        model = command_metamodel.model_from_str("ZEDIT routine", "ZEditCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zedit_abbreviated(self, command_metamodel):
        """ZED routine - abbreviated form"""
        model = command_metamodel.model_from_str("ZED routine", "ZEditCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zedit_with_indirection(self, command_metamodel):
        """ZEDIT @routinename - with indirection"""
        model = command_metamodel.model_from_str("ZEDIT @routinename", "ZEditCommand")
        assert model is not None
        assert len(model.args) == 1
        # Expression structure: Expr.left (UnaryExpr).operand = Indirection
        arg = model.args[0]
        # Navigate: Expr -> left (UnaryExpr) -> operand
        if hasattr(arg, "left"):
            operand = arg.left
            if hasattr(operand, "operand"):
                operand = operand.operand
        else:
            operand = arg
        assert operand.__class__.__name__ == "Indirection"
