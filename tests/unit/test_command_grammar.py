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
    return metamodel_from_file(grammar_dir / "commands.tx", skipws=False)


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

    def test_set_naked_global_target(self, command_metamodel):
        """S ^(1)=value - naked global as SET target (T526 fix)."""
        model = command_metamodel.model_from_str("S ^(1)=100", "SetCommand")
        target = model.assignments[0].targets
        assert target.__class__.__name__ == "NakedGlobal"
        # subscripts is a Subscripts wrapper at grammar level; check args inside
        assert len(target.subscripts.args) == 1

    def test_set_naked_global_multiple_subscripts(self, command_metamodel):
        """S ^(1,2,3)=value - naked global with multiple subscripts (T526 fix)."""
        model = command_metamodel.model_from_str("S ^(1,2,3)=100", "SetCommand")
        target = model.assignments[0].targets
        assert target.__class__.__name__ == "NakedGlobal"
        # subscripts is a Subscripts wrapper at grammar level; check args inside
        assert len(target.subscripts.args) == 3

    def test_set_mixed_global_naked_global(self, command_metamodel):
        """S ^V1(1)=1,^(2)=2 - mix of global and naked global (T526 fix)."""
        model = command_metamodel.model_from_str("S ^V1(1)=1,^(2)=2", "SetCommand")
        assert len(model.assignments) == 2

        # First is GlobalVariable
        target1 = model.assignments[0].targets
        assert target1.__class__.__name__ == "GlobalVariable"
        assert target1.name == "V1"

        # Second is NakedGlobal
        target2 = model.assignments[1].targets
        assert target2.__class__.__name__ == "NakedGlobal"


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

    def test_read_fixed_length(self, command_metamodel):
        """R X#5 (fixed-length read - read exactly 5 characters)"""
        model = command_metamodel.model_from_str("R X#5", "ReadCommand")
        assert len(model.args) == 1
        # fixed_length should be in the ReadTargetWithTimeout
        assert model.args[0].arg.fixed_length is not None
        # Note: fixed_length is an Expr wrapper at grammar level

    def test_read_fixed_length_with_timeout(self, command_metamodel):
        """R X#5:10 (fixed-length read with timeout)"""
        model = command_metamodel.model_from_str("R X#5:10", "ReadCommand")
        assert len(model.args) == 1
        assert model.args[0].arg.fixed_length is not None
        assert model.args[0].arg.timeout is not None
        # Both are Expr wrappers at grammar level

    def test_read_fixed_length_negative(self, command_metamodel):
        """R X#-1 (fixed-length read with negative value - runtime error)"""
        model = command_metamodel.model_from_str("R X#-1", "ReadCommand")
        assert len(model.args) == 1
        assert model.args[0].arg.fixed_length is not None
        # Negative values should still parse, runtime will handle error

    def test_read_fixed_length_variable(self, command_metamodel):
        """R X#N (fixed-length with variable as length)"""
        model = command_metamodel.model_from_str("R X#N", "ReadCommand")
        assert len(model.args) == 1
        assert model.args[0].arg.fixed_length is not None
        # Length is an Expr wrapper containing variable reference

    def test_read_fixed_length_expression(self, command_metamodel):
        """R X#A+B (fixed-length with expression as length)"""
        model = command_metamodel.model_from_str("R X#A+B", "ReadCommand")
        assert len(model.args) == 1
        assert model.args[0].arg.fixed_length is not None


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


class TestQuitFollowedBySet:
    """Tests for QUIT followed by SET - regression tests for T578 bug fix."""

    def test_quit_then_set_with_left_hand_piece(self):
        """Q S $P(X,';')=1 - regression test for T578 bug"""
        from m2py.analysis.command_parser import parse_commands_from_line

        cmds = parse_commands_from_line('Q S $P(X,";")=1')
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[1].__class__.__name__ == "SetCommand"

    def test_quit_postcond_then_set_with_left_hand_piece(self):
        """Q:A='' S $P(X,';')=1 - regression test for T578 bug"""
        from m2py.analysis.command_parser import parse_commands_from_line

        cmds = parse_commands_from_line('Q:A="" S $P(X,";")=1')
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[0].postcond is not None
        assert cmds[1].__class__.__name__ == "SetCommand"

    def test_for_quit_postcond_set_left_hand_piece(self):
        """F I=1:1 Q:A='' S $P(X,';')=1 - regression test for T578 bug (full pattern)"""
        from m2py.analysis.command_parser import parse_commands_from_line

        cmds = parse_commands_from_line('F I=1:1 Q:A="" S $P(X,";")=1')
        assert len(cmds) == 3
        assert cmds[0].__class__.__name__ == "ForCommand"
        assert cmds[1].__class__.__name__ == "QuitCommand"
        assert cmds[2].__class__.__name__ == "SetCommand"

    def test_vv2lhp2_line73_full(self):
        """Full line 73 from VV2LHP2.m - the original failing case"""
        from m2py.analysis.command_parser import parse_commands_from_line

        line = 'F I=1:1 S A=$T(TEX+I),X=Y Q:A=""  S $P(X,$P(A,";",2),$P(A,";",3),$P(A,";",4))=$P(A,";",5),VCOMP=VCOMP_X_" "'
        cmds = parse_commands_from_line(line)
        assert len(cmds) == 4
        assert cmds[0].__class__.__name__ == "ForCommand"
        assert cmds[1].__class__.__name__ == "SetCommand"
        assert cmds[2].__class__.__name__ == "QuitCommand"
        assert cmds[3].__class__.__name__ == "SetCommand"


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
        assert len(getattr(model.args[0], "except")) == 2

    def test_multiple_exclusive_groups(self, command_metamodel):
        """K (X,Y,Z),(X,W) - multiple exclusive groups (intersection)"""
        model = command_metamodel.model_from_str("K (X,Y,Z),(X,W)", "KillCommand")
        assert len(model.args) == 2
        assert model.args[0].exclusive
        assert model.args[1].exclusive
        assert getattr(model.args[0], "except") == ["X", "Y", "Z"]
        assert getattr(model.args[1], "except") == ["X", "W"]

    def test_mixed_exclusive_selective(self, command_metamodel):
        """K (X,W),Z - mixed exclusive and selective"""
        model = command_metamodel.model_from_str("K (X,W),Z", "KillCommand")
        assert len(model.args) == 2
        assert model.args[0].exclusive
        assert getattr(model.args[0], "except") == ["X", "W"]
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

    def test_lock_indirection(self, command_metamodel):
        """L @A - single indirection"""
        model = command_metamodel.model_from_str("L @A", "LockCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        assert target.indirect is not None
        # IndirectChain has var attribute for simple variable
        assert target.indirect.var.name == "A"
        assert target.indirect.nested is None

    def test_lock_double_indirection(self, command_metamodel):
        """L @@A - double indirection"""
        model = command_metamodel.model_from_str("L @@A", "LockCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        assert target.indirect is not None
        # Nested indirection
        assert target.indirect.nested is not None
        assert target.indirect.nested.var.name == "A"

    def test_lock_indirection_with_timeout(self, command_metamodel):
        """L @A:1 - indirection with timeout"""
        model = command_metamodel.model_from_str("L @A:1", "LockCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        assert target.indirect is not None
        assert target.timeout is not None

    def test_lock_paren_with_indirection(self, command_metamodel):
        """L (@A,^B):1 - parenthesized list with indirection"""
        model = command_metamodel.model_from_str("L (@A,^B):1", "LockCommand")
        # Parenthesized list uses locklist instead of targets
        assert model.locklist is not None
        assert len(model.locklist.targets) == 2
        # First item is indirection
        first_item = model.locklist.targets[0]
        assert first_item.indirect is not None
        assert first_item.indirect.var.name == "A"
        # Second item is global
        second_item = model.locklist.targets[1]
        assert second_item.target is not None

    def test_lock_postcond_indirection(self, command_metamodel):
        """L:X=1 @A - postcondition with indirection"""
        model = command_metamodel.model_from_str("L:X=1 @A", "LockCommand")
        assert model.postcond is not None
        assert len(model.targets) == 1
        target = model.targets[0]
        assert target.indirect is not None

    def test_lock_increment(self, command_metamodel):
        """L +^A - lock increment"""
        model = command_metamodel.model_from_str("L +^A", "LockCommand")
        assert model.lockop == "+"
        assert len(model.targets) == 1

    def test_lock_decrement(self, command_metamodel):
        """L -^A - lock decrement"""
        model = command_metamodel.model_from_str("L -^A", "LockCommand")
        assert model.lockop == "-"
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


class TestIndirection:
    """Tests for indirection (@) parsing across all commands.

    All commands use the same Indirection rule from expressions.tx,
    which handles:
    - Single indirection: @VAR
    - Nested indirection: @@VAR (parsed as @(@VAR))
    - Expression indirection: @(expr)
    - Subscripted indirection: @VAR(sub1,sub2)

    DO, GOTO, and LOCK use IndirectChain for additional features
    like @label^routine patterns.
    """

    # --- KILL indirection ---
    def test_kill_indirection(self, command_metamodel):
        """K @A - kill indirection"""
        model = command_metamodel.model_from_str("K @A", "KillCommand")
        assert len(model.args) == 1
        arg = model.args[0]
        assert arg.target is not None
        # target is an Indirection
        assert arg.target.__class__.__name__ == "Indirection"

    def test_kill_double_indirection(self, command_metamodel):
        """K @@A - nested indirection"""
        model = command_metamodel.model_from_str("K @@A", "KillCommand")
        assert len(model.args) == 1
        target = model.args[0].target
        assert target.__class__.__name__ == "Indirection"
        # Nested: expr is also Indirection (textX uses 'expr', not 'expression')
        assert target.expr.__class__.__name__ == "Indirection"

    def test_kill_multiple_indirection(self, command_metamodel):
        """K @A,@B - multiple indirection targets"""
        model = command_metamodel.model_from_str("K @A,@B", "KillCommand")
        assert len(model.args) == 2
        assert model.args[0].target.__class__.__name__ == "Indirection"
        assert model.args[1].target.__class__.__name__ == "Indirection"

    # --- SET indirection ---
    def test_set_target_indirection(self, command_metamodel):
        """S @A=1 - indirection as target"""
        model = command_metamodel.model_from_str("S @A=1", "SetCommand")
        assert len(model.assignments) == 1
        target = model.assignments[0].targets
        assert target.__class__.__name__ == "Indirection"

    def test_set_value_indirection(self, command_metamodel):
        """S X=@A - indirection as value"""
        model = command_metamodel.model_from_str("S X=@A", "SetCommand")
        assert len(model.assignments) == 1
        # Value is an expression containing Indirection
        assert model.assignments[0].value is not None

    def test_set_both_indirection(self, command_metamodel):
        """S @B=@A - indirection on both sides"""
        model = command_metamodel.model_from_str("S @B=@A", "SetCommand")
        assert len(model.assignments) == 1
        target = model.assignments[0].targets
        assert target.__class__.__name__ == "Indirection"

    def test_set_double_indirection(self, command_metamodel):
        """S @@A=1 - nested indirection as target"""
        model = command_metamodel.model_from_str("S @@A=1", "SetCommand")
        target = model.assignments[0].targets
        assert target.__class__.__name__ == "Indirection"
        # textX uses 'expr' attribute
        assert target.expr.__class__.__name__ == "Indirection"

    def test_set_argument_indirection(self, command_metamodel):
        """S @A - argument-level indirection (var contains 'X=1')"""
        model = command_metamodel.model_from_str("S @A", "SetCommand")
        assert len(model.assignments) == 1
        # This uses SetIndirection
        arg = model.assignments[0]
        assert hasattr(arg, "indirect") and arg.indirect is not None

    # --- WRITE indirection (via Expr wrapper) ---
    def test_write_indirection(self, command_metamodel):
        """W @A - indirection as value (wrapped in Expr)"""
        model = command_metamodel.model_from_str("W @A", "WriteCommand")
        assert len(model.args) == 1
        arg = model.args[0].arg
        # WRITE uses Expr which wraps Indirection
        # Need to unwrap: arg.left.operand is the Indirection
        assert arg.__class__.__name__ == "Expr"
        assert arg.left.operand.__class__.__name__ == "Indirection"

    def test_write_double_indirection(self, command_metamodel):
        """W @@C - nested indirection"""
        model = command_metamodel.model_from_str("W @@C", "WriteCommand")
        arg = model.args[0].arg
        # Unwrap Expr to get Indirection
        inner = arg.left.operand
        assert inner.__class__.__name__ == "Indirection"
        assert inner.expr.__class__.__name__ == "Indirection"

    # --- READ indirection ---
    def test_read_indirection(self, command_metamodel):
        """R @A - indirection as target"""
        model = command_metamodel.model_from_str("R @A", "ReadCommand")
        assert len(model.args) == 1
        target = model.args[0].arg.target
        assert target.__class__.__name__ == "Indirection"

    def test_read_multiple_indirection(self, command_metamodel):
        """R @A,@B - multiple indirection targets"""
        model = command_metamodel.model_from_str("R @A,@B", "ReadCommand")
        assert len(model.args) == 2
        assert model.args[0].arg.target.__class__.__name__ == "Indirection"
        assert model.args[1].arg.target.__class__.__name__ == "Indirection"

    # --- HANG indirection (via Expr wrapper) ---
    def test_hang_indirection(self, command_metamodel):
        """H @A - indirection as duration (wrapped in Expr)"""
        model = command_metamodel.model_from_str("H @A", "HangCommand")
        # HangCommand seconds is Expr which wraps Indirection
        assert model.seconds.__class__.__name__ == "Expr"
        assert model.seconds.left.operand.__class__.__name__ == "Indirection"

    # --- FOR indirection ---
    def test_for_indirection_var(self, command_metamodel):
        """F @A=1:1:10 - indirection as loop variable"""
        model = command_metamodel.model_from_str("F @A=1:1:10", "ForCommand")
        assert model.indirect is not None
        assert model.var is None
        assert model.indirect.__class__.__name__ == "Indirection"

    def test_for_double_indirection_var(self, command_metamodel):
        """F @@A=1:1:10 - double indirection as loop variable"""
        model = command_metamodel.model_from_str("F @@A=1:1:10", "ForCommand")
        assert model.indirect is not None
        # textX uses 'expr' attribute for nested
        assert model.indirect.expr.__class__.__name__ == "Indirection"

    def test_for_indirection_params(self, command_metamodel):
        """F I=@A:@B:@C - indirection in parameters"""
        model = command_metamodel.model_from_str("F I=@A:@B:@C", "ForCommand")
        assert model.var is not None
        assert len(model.params) == 1
        # Parameters are Expr wrappers - need to unwrap
        param = model.params[0]
        assert param.start.left.operand.__class__.__name__ == "Indirection"
        assert param.step.left.operand.__class__.__name__ == "Indirection"
        assert param.end.left.operand.__class__.__name__ == "Indirection"

    # --- DO indirection (uses IndirectChain) ---
    def test_do_indirection(self, command_metamodel):
        """D @A - simple DO indirection"""
        model = command_metamodel.model_from_str("D @A", "DoCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        assert target.indirect is not None

    def test_do_double_indirection(self, command_metamodel):
        """D @@A - nested DO indirection via IndirectChain"""
        model = command_metamodel.model_from_str("D @@A", "DoCommand")
        target = model.targets[0]
        # DoIndirect has labelIndirect which is IndirectChain
        assert target.indirect.labelIndirect.nested is not None

    # --- GOTO indirection (uses IndirectChain) ---
    def test_goto_indirection(self, command_metamodel):
        """G @A - simple GOTO indirection"""
        model = command_metamodel.model_from_str("G @A", "GotoCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        assert target.indirect is not None

    def test_goto_double_indirection(self, command_metamodel):
        """G @@A - nested GOTO indirection via IndirectChain"""
        model = command_metamodel.model_from_str("G @@A", "GotoCommand")
        target = model.targets[0]
        # GotoIndirect has labelIndirect which is IndirectChain
        assert target.indirect.labelIndirect.nested is not None
