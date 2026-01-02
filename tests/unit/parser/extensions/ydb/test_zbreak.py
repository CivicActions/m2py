"""Tests for ZBREAK command parsing (YDB extension).

Reference: YottaDB Z-Commands
Migrated from: tests/unit/test_command_grammar.py
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZBreakCommand:
    """Tests for ZBREAK command parsing."""

    def test_zbreak_simple(self, command_metamodel):
        """ZBREAK label - simple breakpoint"""
        model = command_metamodel.model_from_str("ZBREAK label", "ZBreakCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zbreak_abbreviated(self, command_metamodel):
        """ZB label - abbreviated"""
        model = command_metamodel.model_from_str("ZB label", "ZBreakCommand")
        assert len(model.args) == 1

    def test_zbreak_label_routine(self, command_metamodel):
        """ZBREAK label^routine"""
        model = command_metamodel.model_from_str(
            "ZBREAK label^routine", "ZBreakCommand"
        )
        assert len(model.args) == 1

    def test_zbreak_with_action(self, command_metamodel):
        """ZBREAK label:"set x=1" - with action"""
        model = command_metamodel.model_from_str(
            'ZBREAK label:"set x=1"', "ZBreakCommand"
        )
        assert len(model.args) == 1
        assert model.args[0].action is not None

    def test_zbreak_offset(self, command_metamodel):
        """ZBREAK +5^routine - offset into routine"""
        model = command_metamodel.model_from_str("ZBREAK +5^routine", "ZBreakCommand")
        assert len(model.args) == 1

    def test_zbreak_no_args(self, command_metamodel):
        """ZBREAK - remove all breakpoints"""
        model = command_metamodel.model_from_str("ZBREAK", "ZBreakCommand")
        assert len(model.args) == 0


@pytest.mark.parser
@pytest.mark.ydb
class TestZBreakLabelOffset:
    """Tests for ZBREAK label+offset^routine pattern.

    Migrated from: tests/unit/test_command_grammar.py
    """

    def test_zbreak_label_offset_routine(self, command_metamodel):
        """ZBREAK label+offset^routine - common debugger pattern"""
        model = command_metamodel.model_from_str(
            "ZBREAK forcerr+lineno^zbmain", "ZBreakCommand"
        )
        assert len(model.args) == 1
        location = model.args[0].location
        assert location.label == "forcerr"
        assert location.routine == "zbmain"
        assert location.offset is not None

    def test_zbreak_label_offset_routine_with_action(self, command_metamodel):
        """ZBREAK label+offset^routine:action - with action string"""
        model = command_metamodel.model_from_str(
            'ZBREAK label+5^routine:"set x=1"', "ZBreakCommand"
        )
        assert len(model.args) == 1
        assert model.args[0].action is not None
