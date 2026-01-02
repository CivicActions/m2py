"""Tests for General Command Rules parsing (§8.1).

Tests verify the textX grammar correctly captures general command syntax rules.

Reference: MUMPS 1995 ANSI Standard, Section 8.1
"""

import pytest


@pytest.mark.parser
class TestPostconditions:
    """Tests for postcondition parsing across commands (§8.1).

    Migrated from test_command_grammar.py::TestPostconditions.
    """

    def test_set_postcondition(self, command_metamodel):
        """S:X>0 Y=X - SET with command postcondition (§8.1)."""
        model = command_metamodel.model_from_str("S:X>0 Y=X", "SetCommand")
        assert model.postcond is not None
        assert model.postcond.condition is not None

    def test_write_postcondition(self, command_metamodel):
        """W:DEBUG "test" - WRITE with command postcondition (§8.1)."""
        model = command_metamodel.model_from_str('W:DEBUG "test"', "WriteCommand")
        assert model.postcond is not None

    def test_goto_postcondition(self, command_metamodel):
        """G:ERR ERROR - GOTO with command postcondition (§8.1)."""
        model = command_metamodel.model_from_str("G:ERR ERROR", "GotoCommand")
        assert model.postcond is not None

    def test_do_postcondition(self, command_metamodel):
        """D:OK PROCEED - DO with command postcondition (§8.1)."""
        model = command_metamodel.model_from_str("D:OK PROCEED", "DoCommand")
        assert model.postcond is not None

    def test_quit_postcondition(self, command_metamodel):
        """Q:DONE 1 - QUIT with command postcondition (§8.1)."""
        model = command_metamodel.model_from_str("Q:DONE 1", "QuitCommand")
        assert model.postcond is not None


@pytest.mark.parser
class TestArgumentPostconditions:
    """Tests for argument postcondition support per MUMPS spec §8.1.4.

    MUMPS spec §8.1.4: "The postcond may also be used to conditionalize
    the arguments of Do, Goto, and Xecute." This means ONLY these three
    commands support argument-level postconditions.

    Migrated from test_command_grammar.py::TestArgumentPostconditions.
    """

    def test_goto_arg_postcondition_allowed(self, command_metamodel):
        """G ABC:X=1 - GOTO supports argument postconditions (§8.1.4)."""
        model = command_metamodel.model_from_str("G ABC:X=1", "GotoCommand")
        assert model.targets[0].postcond is not None

    def test_do_arg_postcondition_allowed(self, command_metamodel):
        """D LABEL:X=1 - DO supports argument postconditions (§8.1.4)."""
        model = command_metamodel.model_from_str("D LABEL:X=1", "DoCommand")
        assert model.targets[0].postcond is not None

    def test_xecute_arg_postcondition_allowed(self, command_metamodel):
        """X "S X=1":A>0 - XECUTE supports argument postconditions (§8.1.4)."""
        model = command_metamodel.model_from_str('X "S X=1":A>0', "XecuteCommand")
        assert model.postcond is None  # No command postcondition
        assert len(model.args) == 1
        assert model.args[0].postcond is not None

    def test_xecute_multiple_args_with_postconditions(self, command_metamodel):
        """X P,Q:X=10,R:X=10,S - multiple XECUTE args, some with postconditions (§8.1.4)."""
        model = command_metamodel.model_from_str("X P,Q:X=10,R:X=10,S", "XecuteCommand")
        assert len(model.args) == 4
        # P - no postcond
        assert model.args[0].postcond is None
        # Q:X=10 - has postcond
        assert model.args[1].postcond is not None
        # R:X=10 - has postcond
        assert model.args[2].postcond is not None
        # S - no postcond
        assert model.args[3].postcond is None

    def test_xecute_command_and_arg_postconditions(self, command_metamodel):
        """X:P=1 "code1":P=0,"code2":P=1 - both command and arg postconditions (§8.1.4)."""
        model = command_metamodel.model_from_str(
            'X:P=1 "S X=1":P=0,"S Y=2":P=1', "XecuteCommand"
        )
        # Command has postcondition
        assert model.postcond is not None
        # Both args have postconditions
        assert len(model.args) == 2
        assert model.args[0].postcond is not None
        assert model.args[1].postcond is not None

    def test_xecute_numeric_postcondition(self, command_metamodel):
        """X:0 "code":1 - numeric postconditions (0=false, 1=true) (§8.1.4)."""
        model = command_metamodel.model_from_str('X:0 "S V=1":1', "XecuteCommand")
        assert model.postcond is not None  # :0
        assert model.args[0].postcond is not None  # :1

    def test_write_arg_no_postcondition_field(self, command_metamodel):
        """W X - WriteArg has no postcond field (MUMPS spec §8.1.4 compliance)."""
        model = command_metamodel.model_from_str("W X", "WriteCommand")
        # Verify WriteArg does not have postcond attribute
        assert not hasattr(model.args[0], "postcond")

    def test_read_arg_no_postcondition_field(self, command_metamodel):
        """R X - ReadArg has no postcond field (MUMPS spec §8.1.4 compliance)."""
        model = command_metamodel.model_from_str("R X", "ReadCommand")
        # Verify ReadArg does not have postcond attribute
        assert not hasattr(model.args[0], "postcond")

    def test_set_assignment_no_postcondition_field(self, command_metamodel):
        """S X=1 - Assignment has no postcond field (MUMPS spec §8.1.4 compliance)."""
        model = command_metamodel.model_from_str("S X=1", "SetCommand")
        # Verify Assignment does not have postcond attribute
        assert not hasattr(model.assignments[0], "postcond")


@pytest.mark.parser
class TestCommandAbbreviations:
    """Tests for command abbreviations (§8.1).

    Abbreviated forms (S, W, R) must parse identically to full forms (SET, WRITE, READ).
    Per FR-009: abbreviation parity tests.
    """

    def test_set_abbreviation_parity(self, command_metamodel):
        """S X=1 and SET X=1 produce identical ASG structure (§8.1)."""
        model_abbrev = command_metamodel.model_from_str("S X=1", "SetCommand")
        model_full = command_metamodel.model_from_str("SET X=1", "SetCommand")
        assert model_abbrev is not None
        assert model_full is not None
        # Both have same assignment structure
        assert len(model_abbrev.assignments) == len(model_full.assignments)

    def test_write_abbreviation_parity(self, command_metamodel):
        """W X and WRITE X produce identical ASG structure (§8.1)."""
        model_abbrev = command_metamodel.model_from_str("W X", "WriteCommand")
        model_full = command_metamodel.model_from_str("WRITE X", "WriteCommand")
        assert model_abbrev is not None
        assert model_full is not None
        assert len(model_abbrev.args) == len(model_full.args)

    def test_read_abbreviation_parity(self, command_metamodel):
        """R X and READ X produce identical ASG structure (§8.1)."""
        model_abbrev = command_metamodel.model_from_str("R X", "ReadCommand")
        model_full = command_metamodel.model_from_str("READ X", "ReadCommand")
        assert model_abbrev is not None
        assert model_full is not None
        assert len(model_abbrev.args) == len(model_full.args)

    def test_if_abbreviation_parity(self, command_metamodel):
        """I 1 and IF 1 produce identical ASG structure (§8.1)."""
        model_abbrev = command_metamodel.model_from_str("I 1", "IfCommand")
        model_full = command_metamodel.model_from_str("IF 1", "IfCommand")
        assert model_abbrev is not None
        assert model_full is not None
        assert model_abbrev.conditions is not None
        assert model_full.conditions is not None

    def test_for_abbreviation_parity(self, command_metamodel):
        """F I=1:1:10 and FOR I=1:1:10 produce identical ASG structure (§8.1)."""
        model_abbrev = command_metamodel.model_from_str("F I=1:1:10", "ForCommand")
        model_full = command_metamodel.model_from_str("FOR I=1:1:10", "ForCommand")
        assert model_abbrev is not None
        assert model_full is not None
        # Compare variable names (parent references will differ)
        assert model_abbrev.var.name == model_full.var.name

    def test_do_abbreviation_parity(self, command_metamodel):
        """D LABEL and DO LABEL produce identical ASG structure (§8.1)."""
        model_abbrev = command_metamodel.model_from_str("D LABEL", "DoCommand")
        model_full = command_metamodel.model_from_str("DO LABEL", "DoCommand")
        assert model_abbrev is not None
        assert model_full is not None
        assert len(model_abbrev.targets) == len(model_full.targets)

    def test_quit_abbreviation_parity(self, command_metamodel):
        """Q and QUIT produce identical ASG structure (§8.1)."""
        model_abbrev = command_metamodel.model_from_str("Q", "QuitCommand")
        model_full = command_metamodel.model_from_str("QUIT", "QuitCommand")
        assert model_abbrev is not None
        assert model_full is not None
