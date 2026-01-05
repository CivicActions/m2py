"""Tests for HANG command parsing (§8.2.8).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.8
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for HANG command tests."""
    grammar_dir = (
        Path(__file__).parent.parent.parent.parent.parent / "src" / "m2py" / "grammar"
    )
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


@pytest.mark.parser
class TestHangCommandParsing:
    """Parser-level tests for HANG command (§8.2.8)."""

    def test_hang_basic(self, command_metamodel):
        """H 5 - basic hang duration parses correctly (§8.2.8)."""
        model = command_metamodel.model_from_str("H 5", "HangCommand")
        assert len(model.args) == 1
        assert model.args[0].__class__.__name__ == "Expr"

    def test_hang_multiple_args(self, command_metamodel):
        """H 0,1,2,3 - multiple hang durations."""
        model = command_metamodel.model_from_str("H 0,1,2,3", "HangCommand")
        assert len(model.args) == 4
        assert model.postcond is None

    def test_hang_indirection_multiple(self, command_metamodel):
        """H @1,@A - multiple indirections as durations."""
        model = command_metamodel.model_from_str("H @1,@A", "HangCommand")
        assert len(model.args) == 2
        assert model.args[0].left.operand.__class__.__name__ == "Indirection"
        assert model.args[1].left.operand.__class__.__name__ == "Indirection"

    def test_hang_with_postcondition(self, command_metamodel):
        """H:X>0 5 - hang with postcondition."""
        model = command_metamodel.model_from_str("H:X>0 5", "HangCommand")
        assert model.postcond is not None
        assert len(model.args) == 1

    def test_hang_with_simple_postcondition(self, command_metamodel):
        """H:X 5 - hang with simple variable postcondition."""
        model = command_metamodel.model_from_str("H:X 5", "HangCommand")
        assert model.postcond is not None
        assert len(model.args) == 1

    def test_hang_abbreviated(self, command_metamodel):
        """H seconds abbreviation parses correctly (§8.2.8)."""
        model = command_metamodel.model_from_str("H 5", "HangCommand")
        assert len(model.args) == 1
        assert model.postcond is None

    def test_hang_with_decimal(self, command_metamodel):
        """HANG 0.5 decimal seconds parses correctly (§8.2.8)."""
        model = command_metamodel.model_from_str("HANG 0.5", "HangCommand")
        assert len(model.args) == 1

    def test_hang_with_expression(self, command_metamodel):
        """HANG X+Y expression parses correctly (§8.2.8)."""
        model = command_metamodel.model_from_str("H X+Y", "HangCommand")
        assert len(model.args) == 1
