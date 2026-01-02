"""Tests for HANG command parsing (§8.2.8).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.8
"""

import pytest


@pytest.mark.parser
class TestHangCommandParsing:
    """Parser-level tests for HANG command (§8.2.8)."""

    def test_hang_basic(self, command_metamodel):
        """H 5 - HANG with integer seconds (§8.2.8)."""
        model = command_metamodel.model_from_str("H 5", "HangCommand")
        assert len(model.args) == 1
        assert model.args[0].__class__.__name__ == "Expr"

    def test_hang_multiple_args(self, command_metamodel):
        """H 0,1,2,3 - multiple hang durations (§8.2.8)."""
        model = command_metamodel.model_from_str("H 0,1,2,3", "HangCommand")
        assert len(model.args) == 4
        assert model.postcond is None

    def test_hang_indirection_multiple(self, command_metamodel):
        """H @1,@A - multiple indirections as durations (§8.2.8)."""
        model = command_metamodel.model_from_str("H @1,@A", "HangCommand")
        assert len(model.args) == 2
        assert model.args[0].left.operand.__class__.__name__ == "Indirection"
        assert model.args[1].left.operand.__class__.__name__ == "Indirection"

    def test_hang_with_postcondition(self, command_metamodel):
        """H:X>0 5 - hang with postcondition (§8.2.8)."""
        model = command_metamodel.model_from_str("H:X>0 5", "HangCommand")
        assert model.postcond is not None
        assert len(model.args) == 1

    def test_hang_with_simple_postcondition(self, command_metamodel):
        """H:X 5 - hang with simple variable postcondition (§8.2.8)."""
        model = command_metamodel.model_from_str("H:X 5", "HangCommand")
        assert model.postcond is not None
        assert len(model.args) == 1
