"""Tests for ZEDIT command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for ZEDIT command tests."""
    grammar_dir = (
        Path(__file__).parent.parent.parent.parent.parent.parent
        / "src"
        / "m2py"
        / "grammar"
    )
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


@pytest.mark.parser
@pytest.mark.ydb
class TestZeditParsing:
    """Parser-level tests for ZEDIT command (YDB)."""

    def test_zedit_routine(self, command_metamodel):
        """ZEDIT routine - edit a routine."""
        model = command_metamodel.model_from_str("ZEDIT routine", "ZEditCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zedit_abbreviated(self, command_metamodel):
        """ZED routine - abbreviated form."""
        model = command_metamodel.model_from_str("ZED routine", "ZEditCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zedit_with_indirection(self, command_metamodel):
        """ZEDIT @routinename - with indirection."""
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
