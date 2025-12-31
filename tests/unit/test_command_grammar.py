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
        assert model.targets[0].postcond is not None

    def test_goto_computed_offset_with_bare_global(self, command_metamodel):
        """G %389+^V1A-A(^V1A) - computed offset with bare global (Phase 102 Part H)"""
        model = command_metamodel.model_from_str("G %389+^V1A-A(^V1A)", "GotoCommand")
        target = model.targets[0]
        assert target.label.label == "%389"
        assert target.label.offset is not None  # Has computed offset

    def test_goto_computed_offset_multiple_targets(self, command_metamodel):
        """G %Z0+01,ANSI+2,0000000+05 - multiple targets with computed offsets"""
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

    def test_do_computed_offset_with_bare_global(self, command_metamodel):
        """D 1+^V1A^V1CALLE - computed offset with bare global value (Phase 102 Part H)

        Pattern: label=1, offset=^V1A (global value), routine=V1CALLE
        The bare global ^V1A is part of the offset expression, not a routine ref.
        """
        model = command_metamodel.model_from_str("D 1+^V1A^V1CALLE", "DoCommand")
        target = model.targets[0]
        assert target.label.label == "1"
        assert target.label.offset is not None
        assert target.label.routine == "V1CALLE"

    def test_do_computed_offset_complex_expression(self, command_metamodel):
        """D Z+-20+^V1A+^V1A^V1CALLE - complex computed offset with multiple bare globals"""
        model = command_metamodel.model_from_str(
            "D Z+-20+^V1A+^V1A^V1CALLE", "DoCommand"
        )
        target = model.targets[0]
        assert target.label.label == "Z"
        assert target.label.offset is not None
        assert target.label.routine == "V1CALLE"

    def test_do_computed_offset_with_naked_global(self, command_metamodel):
        """D %0A1B2C3+^V1A(2)-^(3)/10 - offset with subscripted and naked globals"""
        model = command_metamodel.model_from_str(
            "D %0A1B2C3+^V1A(2)-^(3)/10", "DoCommand"
        )
        target = model.targets[0]
        assert target.label.label == "%0A1B2C3"
        assert target.label.offset is not None
        # No routine in this case
        assert target.label.routine is None

    def test_do_label_plus_routine_offset_expression(self, command_metamodel):
        """D V1CALLE+7-11+12^V1CALLE - expression offset then routine"""
        model = command_metamodel.model_from_str(
            "D V1CALLE+7-11+12^V1CALLE", "DoCommand"
        )
        target = model.targets[0]
        assert target.label.label == "V1CALLE"
        assert target.label.offset is not None
        assert target.label.routine == "V1CALLE"


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


class TestArgumentPostconditions:
    """Tests for argument postcondition support per MUMPS spec 8.1.4.

    MUMPS spec 8.1.4: "The postcond may also be used to conditionalize
    the arguments of Do, Goto, and Xecute." This means ONLY these three
    commands support argument-level postconditions.
    """

    def test_goto_arg_postcondition_allowed(self, command_metamodel):
        """G ABC:X=1 - GOTO supports argument postconditions"""
        model = command_metamodel.model_from_str("G ABC:X=1", "GotoCommand")
        assert model.targets[0].postcond is not None

    def test_do_arg_postcondition_allowed(self, command_metamodel):
        """D LABEL:X=1 - DO supports argument postconditions"""
        model = command_metamodel.model_from_str("D LABEL:X=1", "DoCommand")
        assert model.targets[0].postcond is not None

    def test_xecute_arg_postcondition_allowed(self, command_metamodel):
        """X "S X=1":A>0 - XECUTE supports argument postconditions (Phase 102 Part I)"""
        model = command_metamodel.model_from_str('X "S X=1":A>0', "XecuteCommand")
        assert model.postcond is None  # No command postcondition
        assert len(model.args) == 1
        assert model.args[0].postcond is not None

    def test_xecute_multiple_args_with_postconditions(self, command_metamodel):
        """X P,Q:X=10,R:X=10,S - multiple XECUTE args, some with postconditions"""
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
        """X:P=1 "code1":P=0,"code2":P=1 - both command and arg postconditions"""
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
        """X:0 "code":1 - numeric postconditions (0=false, 1=true)"""
        model = command_metamodel.model_from_str('X:0 "S V=1":1', "XecuteCommand")
        assert model.postcond is not None  # :0
        assert model.args[0].postcond is not None  # :1

    def test_write_arg_no_postcondition_field(self, command_metamodel):
        """W X - WriteArg has no postcond field (MUMPS spec 8.1.4 compliance)"""
        model = command_metamodel.model_from_str("W X", "WriteCommand")
        # Verify WriteArg does not have postcond attribute
        assert not hasattr(model.args[0], "postcond")

    def test_read_arg_no_postcondition_field(self, command_metamodel):
        """R X - ReadArg has no postcond field (MUMPS spec 8.1.4 compliance)"""
        model = command_metamodel.model_from_str("R X", "ReadCommand")
        # Verify ReadArg does not have postcond attribute
        assert not hasattr(model.args[0], "postcond")

    def test_set_assignment_no_postcondition_field(self, command_metamodel):
        """S X=1 - Assignment has no postcond field (MUMPS spec 8.1.4 compliance)"""
        model = command_metamodel.model_from_str("S X=1", "SetCommand")
        # Verify Assignment does not have postcond attribute
        assert not hasattr(model.assignments[0], "postcond")


class TestQuitFollowedBySet:
    """Tests for QUIT followed by SET - regression tests for T578 bug fix."""

    def test_quit_then_set_with_left_hand_piece(self):
        """Q S $P(X,';')=1 - regression test for T578 bug"""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line('Q S $P(X,";")=1')
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[1].__class__.__name__ == "SetCommand"

    def test_quit_postcond_then_set_with_left_hand_piece(self):
        """Q:A='' S $P(X,';')=1 - regression test for T578 bug"""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line('Q:A="" S $P(X,";")=1')
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[0].postcond is not None
        assert cmds[1].__class__.__name__ == "SetCommand"

    def test_for_quit_postcond_set_left_hand_piece(self):
        """F I=1:1 Q:A='' S $P(X,';')=1 - regression test for T578 bug (full pattern)"""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line('F I=1:1 Q:A="" S $P(X,";")=1')
        assert len(cmds) == 3
        assert cmds[0].__class__.__name__ == "ForCommand"
        assert cmds[1].__class__.__name__ == "QuitCommand"
        assert cmds[2].__class__.__name__ == "SetCommand"

    def test_vv2lhp2_line73_full(self):
        """Full line 73 from VV2LHP2.m - the original failing case"""
        from m2py.parser.line_parser import parse_commands_from_line

        line = 'F I=1:1 S A=$T(TEX+I),X=Y Q:A=""  S $P(X,$P(A,";",2),$P(A,";",3),$P(A,";",4))=$P(A,";",5),VCOMP=VCOMP_X_" "'
        cmds = parse_commands_from_line(line)
        assert len(cmds) == 4
        assert cmds[0].__class__.__name__ == "ForCommand"
        assert cmds[1].__class__.__name__ == "SetCommand"
        assert cmds[2].__class__.__name__ == "QuitCommand"
        assert cmds[3].__class__.__name__ == "SetCommand"


class TestQuitFollowedByTransaction:
    """Tests for QUIT followed by transaction commands - T96.11."""

    def test_quit_then_tstart(self):
        """Q TS - QUIT followed by TSTART (abbreviated)"""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line("Q TS")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[0].value is None  # Q has no return value
        assert cmds[1].__class__.__name__ == "TStartCommand"

    def test_quit_then_tstart_full(self):
        """Q TSTART - QUIT followed by TSTART (full keyword)"""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line("Q TSTART")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[1].__class__.__name__ == "TStartCommand"

    def test_quit_then_tcommit(self):
        """Q TC - QUIT followed by TCOMMIT (abbreviated)"""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line("Q TC")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[1].__class__.__name__ == "TCommitCommand"

    def test_quit_then_trestart(self):
        """Q TRE - QUIT followed by TRESTART (abbreviated)"""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line("Q TRE")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[1].__class__.__name__ == "TRestartCommand"

    def test_quit_then_trollback(self):
        """Q TRO - QUIT followed by TROLLBACK (abbreviated)"""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line("Q TRO")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[1].__class__.__name__ == "TRollbackCommand"

    def test_trollback_then_set(self):
        """TRO S X=1 - TROLLBACK followed by SET (must not consume S as arg)"""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line("TRO S X=1")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "TRollbackCommand"
        assert cmds[1].__class__.__name__ == "SetCommand"

    def test_trollback_with_level(self):
        """TRO 1 - TROLLBACK with level"""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line("TRO 1")
        assert len(cmds) == 1
        assert cmds[0].__class__.__name__ == "TRollbackCommand"
        assert cmds[0].level is not None

    def test_quit_postcond_then_tstart(self):
        """Q:DONE TS - postconditioned QUIT then TSTART"""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line("Q:DONE TS")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[0].postcond is not None
        assert cmds[1].__class__.__name__ == "TStartCommand"


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
        assert len(model.args) == 1
        assert model.args[0].__class__.__name__ == "Expr"

    def test_hang_multiple_args(self, command_metamodel):
        """H 0,1,2,3 - multiple hang durations"""
        model = command_metamodel.model_from_str("H 0,1,2,3", "HangCommand")
        assert len(model.args) == 4
        assert model.postcond is None

    def test_hang_indirection_multiple(self, command_metamodel):
        """H @1,@A - multiple indirections as durations"""
        model = command_metamodel.model_from_str("H @1,@A", "HangCommand")
        assert len(model.args) == 2
        assert model.args[0].left.operand.__class__.__name__ == "Indirection"
        assert model.args[1].left.operand.__class__.__name__ == "Indirection"

    def test_hang_with_postcondition(self, command_metamodel):
        """H:X>0 5 - hang with postcondition"""
        model = command_metamodel.model_from_str("H:X>0 5", "HangCommand")
        assert model.postcond is not None
        assert len(model.args) == 1

    def test_hang_with_simple_postcondition(self, command_metamodel):
        """H:X 5 - hang with simple variable postcondition"""
        model = command_metamodel.model_from_str("H:X 5", "HangCommand")
        assert model.postcond is not None
        assert len(model.args) == 1

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
        """L +^A - incremental lock (lockop on target)"""
        model = command_metamodel.model_from_str("L +^A", "LockCommand")
        assert len(model.targets) == 1
        assert model.targets[0].lockop == "+"

    def test_lock_decrement(self, command_metamodel):
        """L -^A - decremental lock (lockop on target)"""
        model = command_metamodel.model_from_str("L -^A", "LockCommand")
        assert len(model.targets) == 1
        assert model.targets[0].lockop == "-"

    def test_lock_multiple_increments(self, command_metamodel):
        """L +^A,+^B,+^C - multiple incremental locks"""
        model = command_metamodel.model_from_str("L +^A,+^B,+^C", "LockCommand")
        assert len(model.targets) == 3
        assert all(t.lockop == "+" for t in model.targets)

    def test_lock_multiple_decrements(self, command_metamodel):
        """L -^A,-^B,-^C - multiple decremental locks"""
        model = command_metamodel.model_from_str("L -^A,-^B,-^C", "LockCommand")
        assert len(model.targets) == 3
        assert all(t.lockop == "-" for t in model.targets)

    def test_lock_mixed_ops(self, command_metamodel):
        """L +^A,-^B,^C - mixed incremental, decremental, and normal locks"""
        model = command_metamodel.model_from_str("L +^A,-^B,^C", "LockCommand")
        assert len(model.targets) == 3
        assert model.targets[0].lockop == "+"
        assert model.targets[1].lockop == "-"
        assert model.targets[2].lockop is None

    def test_lock_paren_with_ops(self, command_metamodel):
        """L (+^A,+^B):1 - parenthesized with +/- on each item"""
        model = command_metamodel.model_from_str("L (+^A,+^B):1", "LockCommand")
        assert model.locklist is not None
        assert len(model.locklist.targets) == 2
        assert model.locklist.targets[0].lockop == "+"
        assert model.locklist.targets[1].lockop == "+"

    def test_lock_paren_list_lockop(self, command_metamodel):
        """L +(^A,^B,^C) - list-level lockop applies to all items"""
        model = command_metamodel.model_from_str("L +(^A,^B,^C)", "LockCommand")
        assert model.locklist is not None
        assert model.locklist.lockop == "+"
        assert len(model.locklist.targets) == 3

    def test_lock_paren_decremental(self, command_metamodel):
        """L -(^A):1 - decremental lock on parenthesized list with timeout"""
        model = command_metamodel.model_from_str("L -(^A):1", "LockCommand")
        assert model.locklist is not None
        assert model.locklist.lockop == "-"
        assert model.locklist.timeout is not None

    def test_merge(self, command_metamodel):
        """M ^DEST=^SRC"""
        model = command_metamodel.model_from_str("M ^DEST=^SRC", "MergeCommand")
        assert len(model.merges) == 1

    def test_merge_naked_global(self, command_metamodel):
        """M ^(1)=^VV(2) - naked global in MERGE"""
        model = command_metamodel.model_from_str("M ^(1)=^VV(2)", "MergeCommand")
        assert len(model.merges) == 1

    def test_merge_indirection(self, command_metamodel):
        """MERGE @CMD - argument-level indirection in MERGE"""
        model = command_metamodel.model_from_str("MERGE @CMD", "MergeCommand")
        assert len(model.merges) == 1

    def test_set_extended_global_pipe(self, command_metamodel):
        """S ^|"env"|global=1 - pipe-delimited extended global"""
        model = command_metamodel.model_from_str('S ^|"env"|global=1', "SetCommand")
        assert len(model.assignments) == 1

    def test_set_extended_global_bracket(self, command_metamodel):
        """S ^["gld"]global=1 - bracket-delimited extended global"""
        model = command_metamodel.model_from_str('S ^["gld"]global=1', "SetCommand")
        assert len(model.assignments) == 1

    def test_merge_extended_global_pipe(self, command_metamodel):
        """M ^|"dst"|a=^|"src"|b - pipe-delimited extended globals in MERGE"""
        model = command_metamodel.model_from_str(
            'M ^|"dst"|a=^|"src"|b', "MergeCommand"
        )
        assert len(model.merges) == 1

    def test_merge_extended_global_bracket(self, command_metamodel):
        """M ^["dst"]a=^["src"]b - bracket-delimited extended globals in MERGE"""
        model = command_metamodel.model_from_str(
            'M ^["dst"]a=^["src"]b', "MergeCommand"
        )
        assert len(model.merges) == 1

    def test_xecute(self, command_metamodel):
        """X "S X=1" """
        model = command_metamodel.model_from_str('X "S X=1"', "XecuteCommand")
        assert len(model.args) == 1

    def test_view(self, command_metamodel):
        """V 0"""
        model = command_metamodel.model_from_str("V 0", "ViewCommand")
        assert len(model.args) == 1

    def test_view_keyword_value(self, command_metamodel):
        """VIEW "JOBPID":1 - keyword with colon-separated value"""
        model = command_metamodel.model_from_str('VIEW "JOBPID":1', "ViewCommand")
        assert len(model.args) == 1
        # Check that the arg has the colon-separated value
        assert hasattr(model.args[0], "values")
        assert len(model.args[0].values) == 1

    def test_view_keyword_multiple_values(self, command_metamodel):
        """VIEW "trace":1:"^trace" - keyword with multiple colon-separated values"""
        model = command_metamodel.model_from_str(
            'VIEW "trace":1:"^trace"', "ViewCommand"
        )
        assert len(model.args) == 1
        assert len(model.args[0].values) == 2

    def test_view_mixed_case(self, command_metamodel):
        """View "GVDUPSETNOOP":0 - mixed case command"""
        model = command_metamodel.model_from_str('View "GVDUPSETNOOP":0', "ViewCommand")
        assert len(model.args) == 1
        assert len(model.args[0].values) == 1

    def test_view_multiple_args(self, command_metamodel):
        """VIEW "key1":val1,"key2":val2 - multiple comma-separated args"""
        model = command_metamodel.model_from_str(
            'VIEW "key1":val1,"key2":val2', "ViewCommand"
        )
        assert len(model.args) == 2


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
        # HangCommand args are Exprs which wraps the operand
        assert len(model.args) == 1
        assert model.args[0].__class__.__name__ == "Expr"
        assert model.args[0].left.operand.__class__.__name__ == "Indirection"

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

    def test_do_name_indirection(self, command_metamodel):
        """D @X@(1) - name indirection: evaluate X to get label name, append subscript 1"""
        model = command_metamodel.model_from_str("D @X@(1)", "DoCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        assert target.indirect is not None
        # IndirectChain should have name_subscripts
        label_indirect = target.indirect.labelIndirect
        assert label_indirect is not None
        assert hasattr(label_indirect, "name_subscripts")
        assert len(label_indirect.name_subscripts) == 1

    def test_do_chained_name_indirection(self, command_metamodel):
        """D @X@(A)@(B) - chained name indirection: append subscripts A then B"""
        model = command_metamodel.model_from_str("D @X@(A)@(B)", "DoCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        label_indirect = target.indirect.labelIndirect
        assert label_indirect is not None
        assert len(label_indirect.name_subscripts) == 2

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

    def test_goto_name_indirection(self, command_metamodel):
        """G @X@(A) - name indirection: evaluate X to get label name, append subscript A"""
        model = command_metamodel.model_from_str("G @X@(A)", "GotoCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        assert target.indirect is not None
        # IndirectChain should have name_subscripts
        label_indirect = target.indirect.labelIndirect
        assert label_indirect is not None
        assert hasattr(label_indirect, "name_subscripts")
        assert len(label_indirect.name_subscripts) == 1

    def test_goto_chained_name_indirection(self, command_metamodel):
        """G @X@(1)@(2) - chained name indirection: append subscripts 1 then 2"""
        model = command_metamodel.model_from_str("G @X@(1)@(2)", "GotoCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        label_indirect = target.indirect.labelIndirect
        assert label_indirect is not None
        assert len(label_indirect.name_subscripts) == 2

    # --- Triple indirection tests (Phase 102 Part E) ---
    def test_do_triple_indirection(self, command_metamodel):
        """D @@@A - triple DO indirection via nested IndirectChain"""
        model = command_metamodel.model_from_str("D @@@A", "DoCommand")
        target = model.targets[0]
        # IndirectChain nesting: outer.nested.nested
        outer = target.indirect.labelIndirect
        assert outer.nested is not None  # second @
        assert outer.nested.nested is not None  # third @

    def test_goto_triple_indirection(self, command_metamodel):
        """G @@@X - triple GOTO indirection"""
        model = command_metamodel.model_from_str("G @@@X", "GotoCommand")
        target = model.targets[0]
        outer = target.indirect.labelIndirect
        assert outer.nested is not None
        assert outer.nested.nested is not None

    def test_kill_triple_indirection(self, command_metamodel):
        """K @@@X - triple indirection in KILL"""
        model = command_metamodel.model_from_str("K @@@X", "KillCommand")
        target = model.args[0].target
        assert target.__class__.__name__ == "Indirection"
        assert target.expr.__class__.__name__ == "Indirection"
        assert target.expr.expr.__class__.__name__ == "Indirection"

    def test_set_triple_indirection_value(self, command_metamodel):
        """S X=@@@Y - triple indirection in SET value"""
        model = command_metamodel.model_from_str("S X=@@@Y", "SetCommand")
        value = model.assignments[0].value
        # Value is Expr wrapper containing nested indirections
        ind = value.left.operand
        assert ind.__class__.__name__ == "Indirection"
        assert ind.expr.__class__.__name__ == "Indirection"
        assert ind.expr.expr.__class__.__name__ == "Indirection"


# =============================================================================
# Z-Commands (YottaDB/GT.M Extensions)
# =============================================================================


class TestZShowCommand:
    """Tests for ZSHOW command parsing."""

    def test_zshow_simple(self, command_metamodel):
        """ZSHOW "BS" - show breakpoints and stack"""
        model = command_metamodel.model_from_str('ZSHOW "BS"', "ZShowCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zshow_abbreviated(self, command_metamodel):
        """ZSH "V" - abbreviated ZSHOW"""
        model = command_metamodel.model_from_str('ZSH "V"', "ZShowCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zshow_all(self, command_metamodel):
        """ZSHOW "*" - show all"""
        model = command_metamodel.model_from_str('ZSHOW "*"', "ZShowCommand")
        assert len(model.args) == 1

    def test_zshow_with_destination(self, command_metamodel):
        """ZSHOW "V":^RESULT - show variables to global"""
        model = command_metamodel.model_from_str('ZSHOW "V":^RESULT', "ZShowCommand")
        assert len(model.args) == 1
        assert model.args[0].destination is not None

    def test_zshow_no_args(self, command_metamodel):
        """ZSHOW - argumentless"""
        model = command_metamodel.model_from_str("ZSHOW", "ZShowCommand")
        assert len(model.args) == 0

    def test_zshow_postcondition(self, command_metamodel):
        """ZSHOW:X=1 "V" - with postcondition"""
        model = command_metamodel.model_from_str('ZSHOW:X=1 "V"', "ZShowCommand")
        assert model.postcond is not None

    def test_zshow_destination_local(self, command_metamodel):
        """zshow "s":stack - output to local variable"""
        model = command_metamodel.model_from_str('zshow "s":stack', "ZShowCommand")
        assert len(model.args) == 1
        assert model.args[0].destination is not None

    def test_zshow_destination_indirection(self, command_metamodel):
        """ZSHOW "L":@gvar - output with indirection"""
        model = command_metamodel.model_from_str('ZSHOW "L":@gvar', "ZShowCommand")
        assert len(model.args) == 1
        assert model.args[0].destination is not None

    def test_zshow_destination_subscripted_global(self, command_metamodel):
        """ZSHOW "*":^XUTL("XUSYS",$J,"JE") - output to subscripted global"""
        model = command_metamodel.model_from_str(
            'ZSHOW "*":^XUTL("XUSYS",$J,"JE")', "ZShowCommand"
        )
        assert len(model.args) == 1
        assert model.args[0].destination is not None

    def test_zshow_lowercase(self, command_metamodel):
        """zshow "*" - lowercase"""
        model = command_metamodel.model_from_str('zshow "*"', "ZShowCommand")
        assert len(model.args) == 1


class TestZWriteCommand:
    """Tests for ZWRITE command parsing."""

    def test_zwrite_simple(self, command_metamodel):
        """ZWRITE X - write variable X"""
        model = command_metamodel.model_from_str("ZWRITE X", "ZWriteCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zwrite_abbreviated(self, command_metamodel):
        """ZWR X - abbreviated"""
        model = command_metamodel.model_from_str("ZWR X", "ZWriteCommand")
        assert len(model.args) == 1

    def test_zwrite_global(self, command_metamodel):
        """ZWR ^GLOBAL - write global"""
        model = command_metamodel.model_from_str("ZWR ^GLOBAL", "ZWriteCommand")
        assert len(model.args) == 1

    def test_zwrite_indirection(self, command_metamodel):
        """ZWR @var - write via indirection"""
        model = command_metamodel.model_from_str("ZWR @var", "ZWriteCommand")
        assert len(model.args) == 1

    def test_zwrite_no_args(self, command_metamodel):
        """ZWR - write all locals"""
        model = command_metamodel.model_from_str("ZWR", "ZWriteCommand")
        assert len(model.args) == 0


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


class TestZGotoCommand:
    """Tests for ZGOTO command parsing."""

    def test_zgoto_level(self, command_metamodel):
        """ZGOTO 1 - unwind to level 1"""
        model = command_metamodel.model_from_str("ZGOTO 1", "ZGotoCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zgoto_abbreviated(self, command_metamodel):
        """ZGO 0 - abbreviated"""
        model = command_metamodel.model_from_str("ZGO 0", "ZGotoCommand")
        assert len(model.args) == 1

    def test_zgoto_level_target(self, command_metamodel):
        """ZGOTO 1:label^routine - unwind and goto"""
        model = command_metamodel.model_from_str(
            "ZGOTO 1:label^routine", "ZGotoCommand"
        )
        assert len(model.args) == 1
        assert model.args[0].target is not None

    def test_zgoto_zlevel(self, command_metamodel):
        """ZGOTO $ZLEVEL:label - use $ZLEVEL"""
        model = command_metamodel.model_from_str("ZGOTO $ZLEVEL:label", "ZGotoCommand")
        assert len(model.args) == 1

    def test_zgoto_no_args(self, command_metamodel):
        """ZGOTO - return to direct mode"""
        model = command_metamodel.model_from_str("ZGOTO", "ZGotoCommand")
        assert len(model.args) == 0


class TestZKillCommand:
    """Tests for ZKILL command parsing."""

    def test_zkill_simple(self, command_metamodel):
        """ZKILL X - zkill variable"""
        model = command_metamodel.model_from_str("ZKILL X", "ZKillCommand")
        assert model is not None
        assert len(model.targets) == 1

    def test_zkill_abbreviated(self, command_metamodel):
        """ZKI X - abbreviated"""
        model = command_metamodel.model_from_str("ZKI X", "ZKillCommand")
        assert len(model.targets) == 1

    def test_zkill_subscripted(self, command_metamodel):
        """ZKILL X(1) - zkill subscripted variable"""
        model = command_metamodel.model_from_str("ZKILL X(1)", "ZKillCommand")
        assert len(model.targets) == 1


class TestZWithdrawCommand:
    """Tests for ZWITHDRAW command parsing."""

    def test_zwithdraw_simple(self, command_metamodel):
        """ZWITHDRAW X - zwithdraw variable"""
        model = command_metamodel.model_from_str("ZWITHDRAW X", "ZWithdrawCommand")
        assert model is not None
        assert len(model.targets) == 1

    def test_zwithdraw_abbreviated(self, command_metamodel):
        """ZWI X - abbreviated"""
        model = command_metamodel.model_from_str("ZWI X", "ZWithdrawCommand")
        assert len(model.targets) == 1

    def test_zwithdraw_multiple(self, command_metamodel):
        """zwithdraw ^a(1,2),^b - multiple targets"""
        model = command_metamodel.model_from_str(
            "zwithdraw ^a(1,2),^b", "ZWithdrawCommand"
        )
        assert len(model.targets) == 2

    def test_zwithdraw_global(self, command_metamodel):
        """ZWITHDRAW ^GLOBAL - global variable"""
        model = command_metamodel.model_from_str(
            "ZWITHDRAW ^GLOBAL", "ZWithdrawCommand"
        )
        assert len(model.targets) == 1

    def test_zwithdraw_postcondition(self, command_metamodel):
        """zwithdraw:tf X - with postcondition"""
        model = command_metamodel.model_from_str("zwithdraw:tf X", "ZWithdrawCommand")
        assert model.postcond is not None


class TestZHaltCommand:
    """Tests for ZHALT command parsing."""

    def test_zhalt_simple(self, command_metamodel):
        """zhalt 1 - halt with exit code"""
        model = command_metamodel.model_from_str("zhalt 1", "ZHaltCommand")
        assert model is not None
        assert model.exitcode is not None

    def test_zhalt_uppercase(self, command_metamodel):
        """ZHALT 1 - uppercase"""
        model = command_metamodel.model_from_str("ZHALT 1", "ZHaltCommand")
        assert model.exitcode is not None

    def test_zhalt_abbreviated(self, command_metamodel):
        """zh 0 - abbreviated"""
        model = command_metamodel.model_from_str("zh 0", "ZHaltCommand")
        assert model.exitcode is not None

    def test_zhalt_expression(self, command_metamodel):
        """zhalt +$zstatus - with expression"""
        model = command_metamodel.model_from_str("zhalt +$zstatus", "ZHaltCommand")
        assert model.exitcode is not None

    def test_zhalt_postcondition(self, command_metamodel):
        """zhalt:tf 1 - with postcondition"""
        model = command_metamodel.model_from_str("zhalt:tf 1", "ZHaltCommand")
        assert model.postcond is not None
        assert model.exitcode is not None


class TestZAllocateCommand:
    """Tests for ZALLOCATE command parsing."""

    def test_zallocate_simple(self, command_metamodel):
        """za X - simple zallocate"""
        model = command_metamodel.model_from_str("za X", "ZAllocateCommand")
        assert model is not None
        assert len(model.targets) == 1

    def test_zallocate_with_timeout(self, command_metamodel):
        """za X:5 - with timeout"""
        model = command_metamodel.model_from_str("za X:5", "ZAllocateCommand")
        assert len(model.targets) == 1
        assert model.targets[0].timeout is not None

    def test_zallocate_list(self, command_metamodel):
        """Zallocate (@lvar,@gvar):60 - parenthesized list"""
        model = command_metamodel.model_from_str(
            "Zallocate (@lvar,@gvar):60", "ZAllocateCommand"
        )
        assert model.locklist is not None
        assert len(model.locklist.targets) == 2
        assert model.locklist.timeout is not None

    def test_zallocate_postcondition(self, command_metamodel):
        """Zallocate:'(i#2) X - with postcondition"""
        model = command_metamodel.model_from_str(
            "Zallocate:'(i#2) X", "ZAllocateCommand"
        )
        assert model.postcond is not None
        assert len(model.targets) == 1

    def test_zallocate_full(self, command_metamodel):
        """Zallocate:'(i#2) (@lvar,@gvar):60 - full syntax"""
        model = command_metamodel.model_from_str(
            "Zallocate:'(i#2) (@lvar,@gvar):60", "ZAllocateCommand"
        )
        assert model.postcond is not None
        assert model.locklist is not None
        assert len(model.locklist.targets) == 2


class TestZDeallocateCommand:
    """Tests for ZDEALLOCATE command parsing."""

    def test_zdeallocate_simple(self, command_metamodel):
        """zd X - simple zdeallocate"""
        model = command_metamodel.model_from_str("zd X", "ZDeallocateCommand")
        assert model is not None
        assert len(model.targets) == 1

    def test_zdeallocate_full_spelling(self, command_metamodel):
        """zdeallocate X - full spelling"""
        model = command_metamodel.model_from_str("zdeallocate X", "ZDeallocateCommand")
        assert len(model.targets) == 1

    def test_zdeallocate_list(self, command_metamodel):
        """Zdeallocate (@lvar,@gvar) - parenthesized list"""
        model = command_metamodel.model_from_str(
            "Zdeallocate (@lvar,@gvar)", "ZDeallocateCommand"
        )
        assert model.locklist is not None
        assert len(model.locklist.targets) == 2

    def test_zdeallocate_postcondition(self, command_metamodel):
        """Zdeallocate:'(i#2) X - with postcondition"""
        model = command_metamodel.model_from_str(
            "Zdeallocate:'(i#2) X", "ZDeallocateCommand"
        )
        assert model.postcond is not None
        assert len(model.targets) == 1

    def test_zdeallocate_full(self, command_metamodel):
        """Zdeallocate:'(i#2) (@lvar,@gvar) - full syntax from longname test"""
        model = command_metamodel.model_from_str(
            "Zdeallocate:'(i#2) (@lvar,@gvar)", "ZDeallocateCommand"
        )
        assert model.postcond is not None
        assert model.locklist is not None
        assert len(model.locklist.targets) == 2

    def test_zdeallocate_multiple_targets(self, command_metamodel):
        """zd ^a,^b - multiple targets"""
        model = command_metamodel.model_from_str("zd ^a,^b", "ZDeallocateCommand")
        assert len(model.targets) == 2

    def test_zdeallocate_global(self, command_metamodel):
        """ZD ^GLOBAL - global variable"""
        model = command_metamodel.model_from_str("ZD ^GLOBAL", "ZDeallocateCommand")
        assert len(model.targets) == 1


class TestZLinkCommand:
    """Tests for ZLINK command parsing."""

    def test_zlink_simple(self, command_metamodel):
        """ZLINK routine - link routine"""
        model = command_metamodel.model_from_str("ZLINK routine", "ZLinkCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zlink_abbreviated(self, command_metamodel):
        """ZLI routine - abbreviated"""
        model = command_metamodel.model_from_str("ZLI routine", "ZLinkCommand")
        assert len(model.args) == 1

    def test_zlink_string(self, command_metamodel):
        """ZLINK "routine" - string routine name"""
        model = command_metamodel.model_from_str('ZLINK "routine"', "ZLinkCommand")
        assert len(model.args) == 1

    def test_zlink_postcondition(self, command_metamodel):
        """ZLINK:X=1 routine - with postcondition"""
        model = command_metamodel.model_from_str("ZLINK:X=1 routine", "ZLinkCommand")
        assert model.postcond is not None


class TestZPrintCommand:
    """Tests for ZPRINT command parsing."""

    def test_zprint_simple(self, command_metamodel):
        """ZPRINT label - print from label"""
        model = command_metamodel.model_from_str("ZPRINT label", "ZPrintCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zprint_abbreviated(self, command_metamodel):
        """ZP label - abbreviated"""
        model = command_metamodel.model_from_str("ZP label", "ZPrintCommand")
        assert len(model.args) == 1

    def test_zprint_label_routine(self, command_metamodel):
        """ZPRINT label^routine"""
        model = command_metamodel.model_from_str(
            "ZPRINT label^routine", "ZPrintCommand"
        )
        assert len(model.args) == 1

    def test_zprint_no_args(self, command_metamodel):
        """ZPRINT - print current routine"""
        model = command_metamodel.model_from_str("ZPRINT", "ZPrintCommand")
        assert len(model.args) == 0


class TestZSystemCommand:
    """Tests for ZSYSTEM command parsing."""

    def test_zsystem_simple(self, command_metamodel):
        """ZSYSTEM "ls -la" - execute shell command"""
        model = command_metamodel.model_from_str('ZSYSTEM "ls -la"', "ZSystemCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zsystem_abbreviated(self, command_metamodel):
        """ZSY "ls" - abbreviated"""
        model = command_metamodel.model_from_str('ZSY "ls"', "ZSystemCommand")
        assert len(model.args) == 1

    def test_zsystem_variable(self, command_metamodel):
        """ZSYSTEM cmd - variable argument"""
        model = command_metamodel.model_from_str("ZSYSTEM cmd", "ZSystemCommand")
        assert len(model.args) == 1

    def test_zsystem_no_args(self, command_metamodel):
        """ZSYSTEM - spawn interactive shell"""
        model = command_metamodel.model_from_str("ZSYSTEM", "ZSystemCommand")
        assert len(model.args) == 0


class TestZMessageCommand:
    """Tests for ZMESSAGE command parsing."""

    def test_zmessage_simple(self, command_metamodel):
        """ZMESSAGE 150372994 - generate error"""
        model = command_metamodel.model_from_str(
            "ZMESSAGE 150372994", "ZMessageCommand"
        )
        assert model is not None
        assert len(model.args) == 1

    def test_zmessage_abbreviated(self, command_metamodel):
        """ZM err - abbreviated"""
        model = command_metamodel.model_from_str("ZM err", "ZMessageCommand")
        assert len(model.args) == 1


class TestZTriggerCommand:
    """Tests for ZTRIGGER command parsing (Phase 102 Part D)."""

    def test_ztrigger_simple_global(self, command_metamodel):
        """ZTRIGGER ^global - trigger update notification for global"""
        model = command_metamodel.model_from_str("ZTRIGGER ^global", "ZTriggerCommand")
        assert model is not None
        assert model.target is not None
        # target is Expr -> left (UnaryExpr) -> operand (GlobalVariable)
        global_var = model.target.left.operand
        assert global_var.name == "global"

    def test_ztrigger_subscripted_global(self, command_metamodel):
        """ZTRIGGER ^global(sub) - trigger with subscripted global"""
        model = command_metamodel.model_from_str(
            "ZTRIGGER ^global(sub)", "ZTriggerCommand"
        )
        assert model is not None
        global_var = model.target.left.operand
        assert global_var.name == "global"
        assert len(global_var.subscripts.args) == 1

    def test_ztrigger_indirection(self, command_metamodel):
        """ZTRIGGER @gbl - trigger with indirection"""
        model = command_metamodel.model_from_str("ZTRIGGER @gbl", "ZTriggerCommand")
        assert model is not None
        assert model.target is not None

    def test_ztrigger_lowercase(self, command_metamodel):
        """ztrigger ^a - lowercase version"""
        model = command_metamodel.model_from_str("ztrigger ^a", "ZTriggerCommand")
        assert model is not None
        global_var = model.target.left.operand
        assert global_var.name == "a"

    def test_ztrigger_with_postcondition(self, command_metamodel):
        """ZTRIGGER:cond ^a - with postcondition"""
        model = command_metamodel.model_from_str("ZTRIGGER:x ^a", "ZTriggerCommand")
        assert model is not None
        assert model.postcond is not None

    def test_ztrigger_empty_string_subscript(self, command_metamodel):
        """ZTRIGGER ^a("") - with empty string subscript (from test suite)"""
        model = command_metamodel.model_from_str('ZTRIGGER ^a("")', "ZTriggerCommand")
        assert model is not None
        global_var = model.target.left.operand
        assert global_var.name == "a"


class TestZCompileCommand:
    """Tests for ZCOMPILE command parsing."""

    def test_zcompile_simple(self, command_metamodel):
        """ZCOMPILE routine - compile routine"""
        model = command_metamodel.model_from_str("ZCOMPILE routine", "ZCompileCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_zcompile_abbreviated(self, command_metamodel):
        """ZC routine - abbreviated (but note conflict with ZCONTINUE)"""
        # ZC with args should be ZCOMPILE
        model = command_metamodel.model_from_str("ZC routine", "ZCompileCommand")
        assert len(model.args) == 1


class TestZContinueCommand:
    """Tests for ZCONTINUE command parsing."""

    def test_zcontinue_simple(self, command_metamodel):
        """ZCONTINUE - continue from breakpoint"""
        model = command_metamodel.model_from_str("ZCONTINUE", "ZContinueCommand")
        assert model is not None

    def test_zcontinue_lowercase(self, command_metamodel):
        """zcontinue - lowercase"""
        model = command_metamodel.model_from_str("zcontinue", "ZContinueCommand")
        assert model is not None


class TestPartOEdgeCases:
    """Tests for Part O edge cases - miscellaneous grammar fixes.

    These tests cover edge cases found in YottaDB test suites that required
    grammar enhancements in Phase 102 Part O.
    """

    def test_do_with_empty_parens(self, command_metamodel):
        """DO label^routine() - empty parens indicate parameter passing semantics."""
        model = command_metamodel.model_from_str("D LABEL^routine()", "DoCommand")
        assert model is not None
        assert len(model.targets) == 1
        target = model.targets[0]
        # args is on target (DoTarget), not on label (LabelRef)
        assert target.args is not None
        assert len(target.args.args) == 0  # Empty args list
        assert target.label.label == "LABEL"
        assert target.label.routine == "routine"

    def test_do_with_empty_parens_no_routine(self, command_metamodel):
        """DO label() - empty parens with just label."""
        model = command_metamodel.model_from_str("D LABEL()", "DoCommand")
        assert model is not None
        target = model.targets[0]
        assert target.args is not None
        assert len(target.args.args) == 0
        assert target.label.label == "LABEL"

    def test_read_char_into_global(self, command_metamodel):
        """R *^VV("M") - READ single char into global variable."""
        model = command_metamodel.model_from_str('R *^VV("M")', "ReadCommand")
        assert model is not None
        assert len(model.args) == 1
        # ReadArg.arg -> ReadTargetWithTimeout.target -> CharRead
        tat = model.args[0].arg  # ReadTargetWithTimeout
        target = tat.target  # CharRead
        assert target.__class__.__name__ == "CharRead"
        # The var inside CharRead is the actual GlobalVariable (CharReadVar is abstract)
        char_var = target.var
        assert char_var.__class__.__name__ == "GlobalVariable"
        assert char_var.name == "VV"

    def test_read_char_into_local(self, command_metamodel):
        """R *X - READ single char into local variable (baseline)."""
        model = command_metamodel.model_from_str("R *X", "ReadCommand")
        assert model is not None
        tat = model.args[0].arg  # ReadTargetWithTimeout
        target = tat.target  # CharRead
        assert target.__class__.__name__ == "CharRead"

    def test_close_with_keyword(self, command_metamodel):
        """CLOSE file:delete - CLOSE with single keyword parameter."""
        model = command_metamodel.model_from_str("C file:delete", "CloseCommand")
        assert model is not None
        assert len(model.args) == 1
        arg = model.args[0]
        assert arg.device is not None
        assert arg.single_param is not None
        assert arg.single_param.keyword.lower() == "delete"

    def test_close_with_keyword_parens(self, command_metamodel):
        """CLOSE file:(DELETE) - CLOSE with parenthesized keyword."""
        model = command_metamodel.model_from_str("C file:(DELETE)", "CloseCommand")
        assert model is not None
        arg = model.args[0]
        assert arg.device is not None
        assert len(arg.params) == 1
        assert arg.params[0].keyword.upper() == "DELETE"

    def test_close_with_keyword_value(self, command_metamodel):
        """CLOSE file:(RENAME=newfile) - CLOSE with keyword=value."""
        model = command_metamodel.model_from_str(
            "C file:(RENAME=newfile)", "CloseCommand"
        )
        assert model is not None
        arg = model.args[0]
        param = arg.params[0]
        assert param.keyword.upper() == "RENAME"
        assert param.value is not None

    def test_use_with_keyword(self, command_metamodel):
        """USE file:rewind - USE with single keyword parameter."""
        model = command_metamodel.model_from_str("U file:rewind", "UseCommand")
        assert model is not None
        arg = model.args[0]
        assert arg.single_param is not None
        assert arg.single_param.keyword.lower() == "rewind"

    def test_use_with_keyword_value(self, command_metamodel):
        """USE tf:exception="goto EOF" - USE with keyword=value."""
        model = command_metamodel.model_from_str(
            'U tf:exception="goto EOF"', "UseCommand"
        )
        assert model is not None
        arg = model.args[0]
        assert arg.single_param is not None
        assert arg.single_param.keyword.lower() == "exception"
        assert arg.single_param.value is not None

    def test_use_with_multiple_keywords(self, command_metamodel):
        """USE file:(rewind:follow) - USE with multiple keywords."""
        model = command_metamodel.model_from_str("U file:(rewind:follow)", "UseCommand")
        assert model is not None
        arg = model.args[0]
        assert len(arg.params) == 2
        assert arg.params[0].keyword.lower() == "rewind"
        assert arg.params[1].keyword.lower() == "follow"


class TestTextFunctionGrammar:
    """Tests for $TEXT function special grammar.

    $TEXT takes a line reference argument, not a regular expression.
    These tests verify the TextFunction grammar works correctly.
    """

    def test_text_function_with_label(self):
        """$T(label) - TEXT function with label only."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$T(label)\n")
        assert not routine.parse_errors

    def test_text_function_with_label_routine(self):
        """$T(label^routine) - TEXT function with label and routine."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$T(label^routine)\n")
        assert not routine.parse_errors

    def test_text_function_with_offset(self):
        """$T(label+5) - TEXT function with label and offset."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$T(label+5)\n")
        assert not routine.parse_errors

    def test_text_function_with_full_spec(self):
        """$T(label+5^routine) - TEXT function with full specification."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$T(label+5^routine)\n")
        assert not routine.parse_errors

    def test_text_function_with_indirection(self):
        """$T(@VAR) - TEXT function with indirection."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$T(@VAR)\n")
        assert not routine.parse_errors

    def test_text_function_with_routine_indirection(self):
        """$T(^@VAR) - TEXT function with routine indirection."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$T(^@VAR)\n")
        assert not routine.parse_errors

    def test_text_full_keyword(self):
        """$TEXT(label) - full TEXT keyword."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$TEXT(label)\n")
        assert not routine.parse_errors


class TestUnknownCommand:
    """Tests for unknown command detection.

    Phase 101: Unknown commands should raise MUMPSUnknownCommandError during
    parsing when they don't match any recognized MUMPS command pattern.

    The error is caught by parse_line_content() and converted to MParseError
    for error-tolerant parsing.
    """

    def test_unknown_command_raises_error(self):
        """Unknown command like FOOBAR should raise MUMPSUnknownCommandError."""
        from m2py.parser.textx_classes import UnknownCommand
        from m2py.parser.exceptions import MUMPSUnknownCommandError

        with pytest.raises(MUMPSUnknownCommandError) as exc_info:
            UnknownCommand(word="FOOBAR", rest=" X=1")
        assert exc_info.value.command == "FOOBAR"
        assert "Unknown command 'FOOBAR'" in str(exc_info.value)

    def test_unknown_command_preserved_in_parse_error(self):
        """parse_line_content should convert unknown command error to MParseError."""
        from m2py.parser.line_parser import parse_line_content
        from m2py.asg.elements import MParseError

        result = parse_line_content("FOOBAR X=1")
        assert isinstance(result, MParseError)
        assert "FOOBAR" in result.message
        assert "Unknown command" in result.message

    def test_unknown_command_various_patterns(self):
        """Various unknown commands should be caught."""
        from m2py.parser.line_parser import parse_line_content
        from m2py.asg.elements import MParseError

        unknown_commands = [
            "SETUP",  # Not SET (has more letters)
            "WRITEMORE",  # Not WRITE
            "GOSUB",  # Not GO/GOTO
            "ROUTINE",  # Not a command
            "UNKNOWN",
        ]

        for cmd in unknown_commands:
            result = parse_line_content(cmd)
            assert isinstance(result, MParseError), f"Expected MParseError for '{cmd}'"
            assert "Unknown command" in result.message or "Expected" in result.message
