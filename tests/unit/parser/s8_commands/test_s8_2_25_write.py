"""Tests for WRITE command parsing (§8.2.25).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.25

Migrated from: tests/unit/test_command_grammar.py::TestWriteCommand
"""

import pytest


@pytest.mark.parser
class TestWriteCommandParsing:
    """Parser-level tests for WRITE command (§8.2.25)."""

    def test_simple_write(self, command_metamodel):
        """W X - simple variable write (§8.2.25)."""
        model = command_metamodel.model_from_str("W X", "WriteCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_write_string(self, command_metamodel):
        """W "Hello" - string literal write (§8.2.25)."""
        model = command_metamodel.model_from_str('W "Hello"', "WriteCommand")
        assert len(model.args) == 1

    def test_write_newline(self, command_metamodel):
        """W ! - newline format control (§8.2.25)."""
        model = command_metamodel.model_from_str("W !", "WriteCommand")
        assert len(model.args) == 1

    def test_write_adjacent_newlines(self, command_metamodel):
        """W !! - two newlines without comma separator (§8.2.25)."""
        model = command_metamodel.model_from_str("W !!", "WriteCommand")
        assert len(model.args) == 2

    def test_write_triple_newlines(self, command_metamodel):
        """W !!! - three newlines (§8.2.25)."""
        model = command_metamodel.model_from_str("W !!!", "WriteCommand")
        assert len(model.args) == 3

    def test_write_mixed_format_controls(self, command_metamodel):
        """W !!,"Test",! - mix of adjacent and comma-separated (§8.2.25)."""
        model = command_metamodel.model_from_str('W !!,"Test",!', "WriteCommand")
        assert len(model.args) == 4

    def test_write_multiple_args(self, command_metamodel):
        """W "Name: ",NAME,! - multiple arguments (§8.2.25)."""
        model = command_metamodel.model_from_str('W "Name: ",NAME,!', "WriteCommand")
        assert len(model.args) == 3

    def test_write_tab(self, command_metamodel):
        """W ?10 - tab format control (§8.2.25)."""
        model = command_metamodel.model_from_str("W ?10", "WriteCommand")
        assert len(model.args) == 1

    def test_write_form_feed(self, command_metamodel):
        """W # - form feed format control (§8.2.25)."""
        model = command_metamodel.model_from_str("W #", "WriteCommand")
        assert len(model.args) == 1

    def test_write_char_code(self, command_metamodel):
        """W *65 - ASCII character code (§8.2.25)."""
        model = command_metamodel.model_from_str("W *65", "WriteCommand")
        assert len(model.args) == 1

    def test_write_with_postcondition(self, command_metamodel):
        """W:DEBUG "Debug mode" - postconditioned write (§8.2.25)."""
        model = command_metamodel.model_from_str('W:DEBUG "Debug mode"', "WriteCommand")
        assert model.postcond is not None
