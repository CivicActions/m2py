"""Tests for the command grammar (commands.tx).

Low-level tests that verify the textX command grammar directly.
Tests parse individual commands without semantic analysis.

For semantic analysis tests, see test_command_analysis.py.
"""

import pytest
from pathlib import Path
from textx import metamodel_from_file


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar metamodel."""
    grammar_dir = Path(__file__).parent.parent.parent / "src" / "m2py" / "grammar"
    return metamodel_from_file(
        grammar_dir / "commands.tx",
        skipws=False
    )


class TestSetCommand:
    """Tests for SET command parsing."""

    def test_simple_set(self, command_metamodel):
        """SET X=1"""
        model = command_metamodel.model_from_str("S X=1", "SetCommand")
        assert model is not None
        assert len(model.assignments) == 1
        assert model.assignments[0].targets.name == "X"

    def test_set_full_keyword(self, command_metamodel):
        """SET with full keyword"""
        model = command_metamodel.model_from_str("SET X=1", "SetCommand")
        assert model is not None

    def test_set_multiple_assignments(self, command_metamodel):
        """S X=1,Y=2,Z=3"""
        model = command_metamodel.model_from_str("S X=1,Y=2,Z=3", "SetCommand")
        assert len(model.assignments) == 3

    def test_set_with_expression(self, command_metamodel):
        """S X=A+B*C"""
        model = command_metamodel.model_from_str("S X=A+B*C", "SetCommand")
        assert model.assignments[0].value is not None

    def test_set_global(self, command_metamodel):
        """S ^GLOBAL=1"""
        model = command_metamodel.model_from_str("S ^GLOBAL=1", "SetCommand")
        assert model.assignments[0].targets.name == "GLOBAL"

    def test_set_subscripted_global(self, command_metamodel):
        """S ^DATA(1,2)=X"""
        model = command_metamodel.model_from_str("S ^DATA(1,2)=X", "SetCommand")
        assert model is not None

    def test_set_with_postcondition(self, command_metamodel):
        """S:X>0 Y=1"""
        model = command_metamodel.model_from_str("S:X>0 Y=1", "SetCommand")
        assert model.postcond is not None

    def test_set_parenthesized_targets(self, command_metamodel):
        """S (A,B,C)=X"""
        model = command_metamodel.model_from_str("S (A,B,C)=X", "SetCommand")
        targets = model.assignments[0].targets
        assert len(targets.targets) == 3


class TestWriteCommand:
    """Tests for WRITE command parsing."""

    def test_simple_write(self, command_metamodel):
        """W X"""
        model = command_metamodel.model_from_str("W X", "WriteCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_write_string(self, command_metamodel):
        """W "Hello" """
        model = command_metamodel.model_from_str('W "Hello"', "WriteCommand")
        assert len(model.args) == 1

    def test_write_newline(self, command_metamodel):
        """W !"""
        model = command_metamodel.model_from_str("W !", "WriteCommand")
        assert len(model.args) == 1

    def test_write_adjacent_newlines(self, command_metamodel):
        """W !! - two newlines without comma separator"""
        model = command_metamodel.model_from_str("W !!", "WriteCommand")
        assert len(model.args) == 2

    def test_write_triple_newlines(self, command_metamodel):
        """W !!! - three newlines"""
        model = command_metamodel.model_from_str("W !!!", "WriteCommand")
        assert len(model.args) == 3

    def test_write_mixed_format_controls(self, command_metamodel):
        """W !!,"Test",! - mix of adjacent and comma-separated"""
        model = command_metamodel.model_from_str('W !!,"Test",!', "WriteCommand")
        assert len(model.args) == 4

    def test_write_multiple_args(self, command_metamodel):
        """W "Name: ",NAME,!"""
        model = command_metamodel.model_from_str('W "Name: ",NAME,!', "WriteCommand")
        assert len(model.args) == 3

    def test_write_tab(self, command_metamodel):
        """W ?10"""
        model = command_metamodel.model_from_str("W ?10", "WriteCommand")
        assert len(model.args) == 1

    def test_write_form_feed(self, command_metamodel):
        """W #"""
        model = command_metamodel.model_from_str("W #", "WriteCommand")
        assert len(model.args) == 1

    def test_write_char_code(self, command_metamodel):
        """W *65 (ASCII 'A')"""
        model = command_metamodel.model_from_str("W *65", "WriteCommand")
        assert len(model.args) == 1

    def test_write_with_postcondition(self, command_metamodel):
        """W:DEBUG "Debug mode" """
        model = command_metamodel.model_from_str('W:DEBUG "Debug mode"', "WriteCommand")
        assert model.postcond is not None


class TestReadCommand:
    """Tests for READ command parsing."""

    def test_simple_read(self, command_metamodel):
        """R X"""
        model = command_metamodel.model_from_str("R X", "ReadCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_read_multiple_vars(self, command_metamodel):
        """R X,Y,Z - read multiple variables"""
        model = command_metamodel.model_from_str("R X,Y,Z", "ReadCommand")
        assert len(model.args) == 3

    def test_read_with_timeout(self, command_metamodel):
        """R X:30 - timeout is now inside arg.arg (ReadTargetWithTimeout)"""
        model = command_metamodel.model_from_str("R X:30", "ReadCommand")
        # New structure: ReadArg.arg = ReadTargetWithTimeout
        assert model.args[0].arg.timeout is not None

    def test_read_single_char(self, command_metamodel):
        """R *X (single character read)"""
        model = command_metamodel.model_from_str("R *X", "ReadCommand")
        assert len(model.args) == 1


class TestIfElseCommands:
    """Tests for IF and ELSE commands."""

    def test_simple_if(self, command_metamodel):
        """I X=1"""
        model = command_metamodel.model_from_str("I X=1", "IfCommand")
        assert model.conditions is not None
        assert len(model.conditions) == 1

    def test_if_full_keyword(self, command_metamodel):
        """IF X=1"""
        model = command_metamodel.model_from_str("IF X=1", "IfCommand")
        assert model.conditions is not None
        assert len(model.conditions) == 1

    def test_argumentless_if(self, command_metamodel):
        """I (uses $TEST)"""
        model = command_metamodel.model_from_str("I", "IfCommand")
        assert len(model.conditions) == 0

    def test_simple_else(self, command_metamodel):
        """E"""
        model = command_metamodel.model_from_str("E", "ElseCommand")
        assert model is not None

    def test_else_full_keyword(self, command_metamodel):
        """ELSE"""
        model = command_metamodel.model_from_str("ELSE", "ElseCommand")
        assert model is not None


class TestForCommand:
    """Tests for FOR command parsing."""

    def test_simple_for(self, command_metamodel):
        """F I=1:1:10"""
        model = command_metamodel.model_from_str("F I=1:1:10", "ForCommand")
        assert model.var.name == "I"
        assert len(model.params) == 1

    def test_for_step_only(self, command_metamodel):
        """F I=1:1 (infinite loop with step)"""
        model = command_metamodel.model_from_str("F I=1:1", "ForCommand")
        assert model.var.name == "I"

    def test_for_values(self, command_metamodel):
        """F I=1,2,3"""
        model = command_metamodel.model_from_str("F I=1,2,3", "ForCommand")
        assert len(model.params) == 3

    def test_argumentless_for(self, command_metamodel):
        """F (infinite loop)"""
        model = command_metamodel.model_from_str("F", "ForCommand")
        assert model.var is None
    
    def test_subscripted_for_var(self, command_metamodel):
        """F J(1,2,3)=1:1:3 - subscripted loop variable (BUG-003)"""
        model = command_metamodel.model_from_str("F J(1,2,3)=1:1:3", "ForCommand")
        assert model.var.name == "J"
        assert len(model.var.subscripts.args) == 3
        assert len(model.params) == 1
    
    def test_single_subscripted_for_var(self, command_metamodel):
        """F ARR(I)=1:1:10 - single subscript on loop variable"""
        model = command_metamodel.model_from_str("F ARR(I)=1:1:10", "ForCommand")
        assert model.var.name == "ARR"
        assert len(model.var.subscripts.args) == 1


class TestGotoCommand:
    """Tests for GOTO command parsing."""

    def test_simple_goto(self, command_metamodel):
        """G LABEL"""
        model = command_metamodel.model_from_str("G LABEL", "GotoCommand")
        assert len(model.targets) == 1

    def test_goto_with_routine(self, command_metamodel):
        """G LABEL^ROUTINE"""
        model = command_metamodel.model_from_str("G LABEL^ROUTINE", "GotoCommand")
        target = model.targets[0]
        assert target.label.routine == "ROUTINE"

    def test_goto_with_offset(self, command_metamodel):
        """G LABEL+5"""
        model = command_metamodel.model_from_str("G LABEL+5", "GotoCommand")
        target = model.targets[0]
        assert target.label.offset is not None

    def test_goto_conditional(self, command_metamodel):
        """G:X LABEL"""
        model = command_metamodel.model_from_str("G:X LABEL", "GotoCommand")
        assert model.postcond is not None
    
    def test_goto_arg_postcondition(self, command_metamodel):
        """G ABC:X=1 - postcondition on target argument (BUG-004)"""
        model = command_metamodel.model_from_str("G ABC:X=1", "GotoCommand")
        assert model.postcond is None  # Command postcond is None
        assert model.targets[0].postcond is not None  # Target postcond is set
        assert model.targets[0].label.label == "ABC"
    
    def test_goto_multiple_arg_postconditions(self, command_metamodel):
        """G ABC:X=1,DEF:Y=2 - multiple targets with postconditions"""
        model = command_metamodel.model_from_str("G ABC:X=1,DEF:Y=2", "GotoCommand")
        assert len(model.targets) == 2
        assert model.targets[0].postcond is not None
        assert model.targets[1].postcond is not None


class TestDoCommand:
    """Tests for DO command parsing."""

    def test_simple_do(self, command_metamodel):
        """D LABEL"""
        model = command_metamodel.model_from_str("D LABEL", "DoCommand")
        assert len(model.targets) == 1

    def test_do_with_args(self, command_metamodel):
        """D LABEL(A,B)"""
        model = command_metamodel.model_from_str("D LABEL(A,B)", "DoCommand")
        target = model.targets[0]
        assert target.args is not None

    def test_do_external_routine(self, command_metamodel):
        """D ^ROUTINE"""
        model = command_metamodel.model_from_str("D ^ROUTINE", "DoCommand")
        target = model.targets[0]
        assert target.label.routine == "ROUTINE"

    def test_argumentless_do(self, command_metamodel):
        """D (block start)"""
        model = command_metamodel.model_from_str("D", "DoCommand")
        assert model.targets is None or len(model.targets) == 0
    
    def test_do_arg_postcondition(self, command_metamodel):
        """D LABEL:X=1 - postcondition on target argument (BUG-004)"""
        model = command_metamodel.model_from_str("D LABEL:X=1", "DoCommand")
        assert model.postcond is None  # Command postcond is None
        assert model.targets[0].postcond is not None  # Target postcond is set
        assert model.targets[0].label.label == "LABEL"


class TestQuitCommand:
    """Tests for QUIT command parsing."""

    def test_simple_quit(self, command_metamodel):
        """Q"""
        model = command_metamodel.model_from_str("Q", "QuitCommand")
        assert model.value is None

    def test_quit_with_value(self, command_metamodel):
        """Q X+Y"""
        model = command_metamodel.model_from_str("Q X+Y", "QuitCommand")
        assert model.value is not None

    def test_quit_conditional(self, command_metamodel):
        """Q:DONE"""
        model = command_metamodel.model_from_str("Q:DONE", "QuitCommand")
        assert model.postcond is not None


class TestNewKillCommands:
    """Tests for NEW and KILL commands."""

    def test_simple_new(self, command_metamodel):
        """N X"""
        model = command_metamodel.model_from_str("N X", "NewCommand")
        assert len(model.vars) == 1

    def test_new_multiple(self, command_metamodel):
        """N X,Y,Z"""
        model = command_metamodel.model_from_str("N X,Y,Z", "NewCommand")
        assert len(model.vars) == 3

    def test_exclusive_new(self, command_metamodel):
        """N (X) - new all except X"""
        model = command_metamodel.model_from_str("N (X)", "NewCommand")
        assert model.exclusive is not None

    def test_simple_kill(self, command_metamodel):
        """K X"""
        model = command_metamodel.model_from_str("K X", "KillCommand")
        assert len(model.args) == 1
        assert model.args[0].target is not None
        assert not model.args[0].exclusive  # False when not exclusive

    def test_kill_global(self, command_metamodel):
        """K ^GLOBAL"""
        model = command_metamodel.model_from_str("K ^GLOBAL", "KillCommand")
        assert len(model.args) == 1
        assert model.args[0].target is not None

    def test_exclusive_kill(self, command_metamodel):
        """K (X,Y)"""
        model = command_metamodel.model_from_str("K (X,Y)", "KillCommand")
        assert len(model.args) == 1
        assert model.args[0].exclusive  # True-ish when exclusive
        # textX uses 'except' attribute name from grammar
        assert len(getattr(model.args[0], 'except')) == 2

    def test_multiple_exclusive_groups(self, command_metamodel):
        """K (X,Y,Z),(X,W) - multiple exclusive groups (intersection)"""
        model = command_metamodel.model_from_str("K (X,Y,Z),(X,W)", "KillCommand")
        assert len(model.args) == 2
        assert model.args[0].exclusive
        assert model.args[1].exclusive
        assert getattr(model.args[0], 'except') == ["X", "Y", "Z"]
        assert getattr(model.args[1], 'except') == ["X", "W"]

    def test_mixed_exclusive_selective(self, command_metamodel):
        """K (X,W),Z - mixed exclusive and selective"""
        model = command_metamodel.model_from_str("K (X,W),Z", "KillCommand")
        assert len(model.args) == 2
        assert model.args[0].exclusive
        assert getattr(model.args[0], 'except') == ["X", "W"]
        assert model.args[1].target is not None


class TestOtherCommands:
    """Tests for other commands."""

    def test_hang(self, command_metamodel):
        """H 5"""
        model = command_metamodel.model_from_str("H 5", "HangCommand")
        assert model.seconds is not None

    def test_halt(self, command_metamodel):
        """HALT"""
        model = command_metamodel.model_from_str("HALT", "HaltCommand")
        assert model is not None

    def test_break(self, command_metamodel):
        """B"""
        model = command_metamodel.model_from_str("B", "BreakCommand")
        assert model is not None

    def test_lock(self, command_metamodel):
        """L ^GLOBAL"""
        model = command_metamodel.model_from_str("L ^GLOBAL", "LockCommand")
        assert len(model.targets) == 1

    def test_merge(self, command_metamodel):
        """M ^DEST=^SRC"""
        model = command_metamodel.model_from_str("M ^DEST=^SRC", "MergeCommand")
        assert len(model.merges) == 1

    def test_xecute(self, command_metamodel):
        """X "S X=1" """
        model = command_metamodel.model_from_str('X "S X=1"', "XecuteCommand")
        assert len(model.args) == 1

    def test_view(self, command_metamodel):
        """V 0"""
        model = command_metamodel.model_from_str("V 0", "ViewCommand")
        assert len(model.args) == 1


class TestPostconditions:
    """Tests for postcondition parsing across commands."""

    def test_set_postcondition(self, command_metamodel):
        """S:X>0 Y=X"""
        model = command_metamodel.model_from_str("S:X>0 Y=X", "SetCommand")
        assert model.postcond is not None
        assert model.postcond.condition is not None

    def test_write_postcondition(self, command_metamodel):
        """W:DEBUG "test" """
        model = command_metamodel.model_from_str('W:DEBUG "test"', "WriteCommand")
        assert model.postcond is not None

    def test_goto_postcondition(self, command_metamodel):
        """G:ERR ERROR"""
        model = command_metamodel.model_from_str("G:ERR ERROR", "GotoCommand")
        assert model.postcond is not None

    def test_do_postcondition(self, command_metamodel):
        """D:OK PROCEED"""
        model = command_metamodel.model_from_str("D:OK PROCEED", "DoCommand")
        assert model.postcond is not None

    def test_quit_postcondition(self, command_metamodel):
        """Q:DONE 1"""
        model = command_metamodel.model_from_str("Q:DONE 1", "QuitCommand")
        assert model.postcond is not None
