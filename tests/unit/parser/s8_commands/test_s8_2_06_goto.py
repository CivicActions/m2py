"""Tests for GOTO command parsing (§8.2.6).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.6
Migrated from: tests/unit/test_command_grammar.py::TestGotoCommand
"""

import pytest


@pytest.mark.parser
class TestGotoCommandParsing:
    """Parser-level tests for GOTO command (§8.2.6)."""

    def test_simple_goto(self, command_metamodel):
        """G LABEL - simple goto parses correctly (§8.2.6)."""
        model = command_metamodel.model_from_str("G LABEL", "GotoCommand")
        assert len(model.targets) == 1

    def test_goto_with_routine(self, command_metamodel):
        """G LABEL^ROUTINE - goto with external routine (§8.2.6)."""
        model = command_metamodel.model_from_str("G LABEL^ROUTINE", "GotoCommand")
        target = model.targets[0]
        assert target.label.routine == "ROUTINE"

    def test_goto_with_offset(self, command_metamodel):
        """G LABEL+5 - goto with offset (§8.2.6)."""
        model = command_metamodel.model_from_str("G LABEL+5", "GotoCommand")
        target = model.targets[0]
        assert target.label.offset is not None

    def test_goto_conditional(self, command_metamodel):
        """G:X LABEL - goto with command postcondition (§8.2.6)."""
        model = command_metamodel.model_from_str("G:X LABEL", "GotoCommand")
        assert model.postcond is not None

    def test_goto_arg_postcondition(self, command_metamodel):
        """G ABC:X=1 - postcondition on target argument (§8.2.6, BUG-004)."""
        model = command_metamodel.model_from_str("G ABC:X=1", "GotoCommand")
        assert model.postcond is None  # Command postcond is None
        assert model.targets[0].postcond is not None  # Target postcond is set
        assert model.targets[0].label.label == "ABC"

    def test_goto_multiple_arg_postconditions(self, command_metamodel):
        """G ABC:X=1,DEF:Y=2 - multiple targets with postconditions (§8.2.6)."""
        model = command_metamodel.model_from_str("G ABC:X=1,DEF:Y=2", "GotoCommand")
        assert len(model.targets) == 2
        assert model.targets[0].postcond is not None
        assert model.targets[0].postcond is not None

    def test_goto_computed_offset_with_bare_global(self, command_metamodel):
        """G %389+^V1A-A(^V1A) - computed offset with bare global (§8.2.6)."""
        model = command_metamodel.model_from_str("G %389+^V1A-A(^V1A)", "GotoCommand")
        target = model.targets[0]
        assert target.label.label == "%389"
        assert target.label.offset is not None  # Has computed offset

    def test_goto_computed_offset_multiple_targets(self, command_metamodel):
        """G %Z0+01,ANSI+2,0000000+05 - multiple targets with computed offsets (§8.2.6)."""
        model = command_metamodel.model_from_str(
            "G %Z0+01,ANSI+2,0000000+05", "GotoCommand"
        )
        assert len(model.targets) == 3
        # First target: %Z0+01
        assert model.targets[0].label.label == "%Z0"
        assert model.targets[0].label.offset is not None
        # Second target: ANSI+2
        assert model.targets[1].label.label == "ANSI"
        # Third target: 0000000+05
        assert model.targets[2].label.label == "0000000"
