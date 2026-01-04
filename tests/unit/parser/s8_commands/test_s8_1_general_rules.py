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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: command spacing")
    def test_command_spacing(self, parse_line):
        """Command with proper spacing parses correctly (§8.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: command comment")
    def test_command_comment(self, parse_line):
        """Command followed by comment ; parses correctly (§8.1)."""
        pytest.fail("Stub - implement test")

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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: command timeout")
    def test_command_timeout(self, parse_line):
        """Command with timeout CMD:timeout arg parses correctly (§8.1)."""
        pytest.fail("Stub - implement test")


@pytest.mark.parser
class TestCommandAbbreviations:
    """Tests for command abbreviations (§8.1).

    Abbreviated forms (S, W, R) must parse identically to full forms (SET, WRITE, READ).
    Per FR-009: abbreviation parity tests.
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: SET abbreviation parity")
    def test_set_abbreviation_parity(self, parse_line):
        """S X=1 and SET X=1 produce identical ASG structure (§8.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: WRITE abbreviation parity")
    def test_write_abbreviation_parity(self, parse_line):
        """W X and WRITE X produce identical ASG structure (§8.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ abbreviation parity")
    def test_read_abbreviation_parity(self, parse_line):
        """R X and READ X produce identical ASG structure (§8.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: IF abbreviation parity")
    def test_if_abbreviation_parity(self, parse_line):
        """I cond and IF cond produce identical ASG structure (§8.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR abbreviation parity")
    def test_for_abbreviation_parity(self, parse_line):
        """F i=1:1:10 and FOR i=1:1:10 produce identical ASG structure (§8.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO abbreviation parity")
    def test_do_abbreviation_parity(self, parse_line):
        """D label and DO label produce identical ASG structure (§8.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: QUIT abbreviation parity")
    def test_quit_abbreviation_parity(self, parse_line):
        """Q and QUIT produce identical ASG structure (§8.1)."""
        pytest.fail("Stub - implement test")


@pytest.mark.parser
class TestArgumentPostconditions:
    """Tests for argument postcondition support per MUMPS spec 8.1.4.

    MUMPS spec 8.1.4: "The postcond may also be used to conditionalize
    the arguments of Do, Goto, and Xecute." This means ONLY these three
    commands support argument-level postconditions.
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
        """X \"S X=1\":A>0 - XECUTE supports argument postconditions (§8.1.4)."""
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


@pytest.mark.parser
class TestPostconditions:
    """Tests for postcondition parsing (§8.1)."""

    def test_goto_postcondition(self, command_metamodel):
        """G:ERR ERROR - GOTO with postcondition (§8.1)."""
        model = command_metamodel.model_from_str("G:ERR ERROR", "GotoCommand")
        assert model.postcond is not None

    def test_do_postcondition(self, command_metamodel):
        """D:OK PROCEED - DO with postcondition (§8.1)."""
        model = command_metamodel.model_from_str("D:OK PROCEED", "DoCommand")
        assert model.postcond is not None
