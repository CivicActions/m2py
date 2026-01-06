"""Tests for General Command Rules parsing (§8.1).

Tests verify the textX grammar correctly captures general command syntax rules.

Reference: MUMPS 1995 ANSI Standard, Section 8.1
"""

import pytest
from pathlib import Path
from textx import metamodel_from_file
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))
from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar metamodel with custom classes."""
    grammar_dir = (
        Path(__file__).parent.parent.parent.parent.parent / "src" / "m2py" / "grammar"
    )
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


@pytest.mark.parser
class TestGeneralCommandRulesParsing:
    """Parser-level tests for General Command Rules (§8.1).

    Covers command spaces, comments, postconditions, timeouts, and abbreviations.
    """

    def test_command_spacing(self, command_metamodel):
        """Command with proper spacing parses correctly (§8.1).

        Commands require a space between the command word and arguments.
        """
        # Single space between command and argument
        model = command_metamodel.model_from_str("S X=1", "SetCommand")
        assert model is not None
        assert len(model.assignments) == 1

        # Multiple arguments separated by commas
        model = command_metamodel.model_from_str("W X,Y,Z", "WriteCommand")
        assert len(model.args) == 3

    def test_command_comment(self, command_metamodel):
        """Command followed by comment ; parses correctly (§8.1).

        Comments start with ; and continue to end of line.
        At the grammar level, comments are handled by the line parser,
        so we verify commands parse correctly. The comment is stripped
        before reaching the command parser.
        """
        # Verify SET command parses - comments are stripped at line level
        model = command_metamodel.model_from_str("S X=1", "SetCommand")
        assert model is not None
        assert len(model.assignments) == 1

        # Verify WRITE command parses
        model = command_metamodel.model_from_str("W X,Y", "WriteCommand")
        assert model is not None
        assert len(model.args) == 2

    def test_command_postcondition(self, command_metamodel):
        """Command with postcondition CMD:condition arg parses correctly (§8.1)."""
        model = command_metamodel.model_from_str("G:ERR ERROR", "GotoCommand")
        assert model.postcond is not None
        model = command_metamodel.model_from_str("D:OK PROCEED", "DoCommand")
        assert model.postcond is not None

    def test_argument_postcondition(self, command_metamodel):
        """Argument with postcondition CMD arg:condition parses correctly (§8.1)."""
        model = command_metamodel.model_from_str("G ABC:X=1", "GotoCommand")
        assert model.targets[0].postcond is not None
        model = command_metamodel.model_from_str("D LABEL:X=1", "DoCommand")
        assert model.targets[0].postcond is not None
        model = command_metamodel.model_from_str('X "S X=1":A>0', "XecuteCommand")
        assert model.postcond is None  # No command postcondition
        assert len(model.args) == 1
        assert model.args[0].postcond is not None

    def test_command_timeout(self, command_metamodel):
        """Command with timeout parses correctly (§8.1).

        Timeout syntax varies by command:
        - READ X:timeout - read with timeout
        - LOCK +^GBL:timeout - lock with timeout
        - JOB label::timeout - job with timeout (after processparams)
        """
        # READ with timeout
        model = command_metamodel.model_from_str("R X:5", "ReadCommand")
        assert model is not None
        assert len(model.args) == 1
        # The timeout is in the ReadTargetWithTimeout (accessed via arg.arg)
        assert model.args[0].arg.timeout is not None

        # LOCK with timeout - uses targets, not args
        model = command_metamodel.model_from_str("L +^GBL:10", "LockCommand")
        assert model is not None
        # Lock target has timeout
        assert model.targets[0].timeout is not None


@pytest.mark.parser
class TestCommandAbbreviations:
    """Tests for command abbreviations (§8.1).

    Abbreviated forms (S, W, R) must parse identically to full forms (SET, WRITE, READ).
    Per FR-009: abbreviation parity tests.
    """

    def test_set_abbreviation_parity(self, command_metamodel):
        """S X=1 and SET X=1 produce identical parse structure (§8.1)."""
        abbrev = command_metamodel.model_from_str("S X=1", "SetCommand")
        full = command_metamodel.model_from_str("SET X=1", "SetCommand")

        # Both should parse to SetCommand with same structure
        assert abbrev.__class__.__name__ == full.__class__.__name__
        assert len(abbrev.assignments) == len(full.assignments)
        assert abbrev.assignments[0].targets.name == full.assignments[0].targets.name

    def test_write_abbreviation_parity(self, command_metamodel):
        """W X and WRITE X produce identical parse structure (§8.1)."""
        abbrev = command_metamodel.model_from_str("W X", "WriteCommand")
        full = command_metamodel.model_from_str("WRITE X", "WriteCommand")

        assert abbrev.__class__.__name__ == full.__class__.__name__
        assert len(abbrev.args) == len(full.args)

    def test_read_abbreviation_parity(self, command_metamodel):
        """R X and READ X produce identical parse structure (§8.1)."""
        abbrev = command_metamodel.model_from_str("R X", "ReadCommand")
        full = command_metamodel.model_from_str("READ X", "ReadCommand")

        assert abbrev.__class__.__name__ == full.__class__.__name__
        assert len(abbrev.args) == len(full.args)

    def test_if_abbreviation_parity(self, command_metamodel):
        """I X and IF X produce identical parse structure (§8.1)."""
        abbrev = command_metamodel.model_from_str("I X", "IfCommand")
        full = command_metamodel.model_from_str("IF X", "IfCommand")

        assert abbrev.__class__.__name__ == full.__class__.__name__
        # Both have conditions (plural)
        assert len(abbrev.conditions) == len(full.conditions)

    def test_for_abbreviation_parity(self, command_metamodel):
        """F i=1:1:10 and FOR i=1:1:10 produce identical parse structure (§8.1)."""
        abbrev = command_metamodel.model_from_str("F i=1:1:10", "ForCommand")
        full = command_metamodel.model_from_str("FOR i=1:1:10", "ForCommand")

        assert abbrev.__class__.__name__ == full.__class__.__name__
        # Both have loop variable (var)
        assert abbrev.var is not None
        assert full.var is not None

    def test_do_abbreviation_parity(self, command_metamodel):
        """D label and DO label produce identical parse structure (§8.1)."""
        abbrev = command_metamodel.model_from_str("D label", "DoCommand")
        full = command_metamodel.model_from_str("DO label", "DoCommand")

        assert abbrev.__class__.__name__ == full.__class__.__name__
        assert len(abbrev.targets) == len(full.targets)

    def test_quit_abbreviation_parity(self, command_metamodel):
        """Q and QUIT produce identical parse structure (§8.1)."""
        abbrev = command_metamodel.model_from_str("Q", "QuitCommand")
        full = command_metamodel.model_from_str("QUIT", "QuitCommand")

        assert abbrev.__class__.__name__ == full.__class__.__name__
        # Both should have no return value
        assert abbrev.value is None
        assert full.value is None


@pytest.mark.parser
class TestArgumentPostconditions:
    """Tests for argument postcondition support per MUMPS spec 8.1.4.

    MUMPS spec 8.1.4: "The postcond may also be used to conditionalize
    the arguments of Do, Goto, and Xecute." This means ONLY these three
    commands support argument-level postconditions.
    """

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
        """X:P=1 \"code1\":P=0,\"code2\":P=1 - both command and arg postconditions (§8.1.4)."""
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
        """X:0 \"code\":1 - numeric postconditions (0=false, 1=true) (§8.1.4)."""
        model = command_metamodel.model_from_str('X:0 "S V=1":1', "XecuteCommand")
        assert model.postcond is not None  # :0
        assert model.args[0].postcond is not None  # :1

    def test_write_arg_no_postcondition_field(self, command_metamodel):
        """W X - WriteArg has no postcond field (MUMPS spec 8.1.4 compliance)."""
        model = command_metamodel.model_from_str("W X", "WriteCommand")
        # Verify WriteArg does not have postcond attribute
        assert not hasattr(model.args[0], "postcond")

    def test_read_arg_no_postcondition_field(self, command_metamodel):
        """R X - ReadArg has no postcond field (MUMPS spec 8.1.4 compliance)."""
        model = command_metamodel.model_from_str("R X", "ReadCommand")
        # Verify ReadArg does not have postcond attribute
        assert not hasattr(model.args[0], "postcond")

    def test_set_assignment_no_postcondition_field(self, command_metamodel):
        """S X=1 - Assignment has no postcond field (MUMPS spec 8.1.4 compliance)."""
        model = command_metamodel.model_from_str("S X=1", "SetCommand")
        # Verify Assignment does not have postcond attribute
        assert not hasattr(model.assignments[0], "postcond")
