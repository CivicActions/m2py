"""Tests for IF command ASG analysis (§8.2.9).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.9
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command, SemanticAnalyzer
from m2py.asg.statements import (
    MIfStatement,
    MElseStatement,
    MForStatement,
    MSetStatement,
    MWriteStatement,
)


@pytest.mark.asg
class TestIfCommandAnalysis:
    """ASG-level tests for IF command analysis (§8.2.9)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: IF $TEST modification")
    def test_if_test_modification(self, analyze_routine):
        """IF modifies $TEST correctly (§8.2.9)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: IF condition analysis")
    def test_if_condition_analysis(self, analyze_routine):
        """IF condition expressions are analyzed (§8.2.9)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: IF control flow")
    def test_if_control_flow(self, analyze_routine):
        """IF control flow impact is tracked (§8.2.9)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: IF argumentless")
    def test_if_argumentless(self, analyze_routine):
        """IF argumentless uses $TEST (§8.2.9)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: IF multiple conditions")
    def test_if_multiple_conditions(self, analyze_routine):
        """IF with multiple comma-separated conditions is analyzed (§8.2.9)."""
        pytest.fail("Stub - implement test")


@pytest.mark.asg
class TestIfElseBodyPopulation:
    """Tests for IF/ELSE body statement collection (§8.2.9, §8.2.4)."""

    def test_if_body_single_command(self):
        """IF captures single following command in then_scope."""
        parser = MUMPSParser()
        source = "TEST\tI X=1 S Y=2\n"
        routine = parser.parse(source)

        if_stmt = routine.labels[0].body.statements[0]
        assert isinstance(if_stmt, MIfStatement)
        assert len(if_stmt.then_scope.statements) == 1
        assert isinstance(if_stmt.then_scope.statements[0], MSetStatement)

    def test_if_body_multiple_commands(self):
        """IF captures multiple following commands in then_scope."""
        parser = MUMPSParser()
        source = "TEST\tI X=1 S Y=2 W Y\n"
        routine = parser.parse(source)

        if_stmt = routine.labels[0].body.statements[0]
        assert isinstance(if_stmt, MIfStatement)
        assert len(if_stmt.then_scope.statements) == 2
        assert isinstance(if_stmt.then_scope.statements[0], MSetStatement)
        assert isinstance(if_stmt.then_scope.statements[1], MWriteStatement)

    def test_else_body_commands(self):
        """ELSE captures following commands in body."""
        parser = MUMPSParser()
        source = "TEST\tE  S Y=3 W Y\n"
        routine = parser.parse(source)

        else_stmt = routine.labels[0].body.statements[0]
        assert isinstance(else_stmt, MElseStatement)
        assert len(else_stmt.body.statements) == 2
        assert isinstance(else_stmt.body.statements[0], MSetStatement)
        assert isinstance(else_stmt.body.statements[1], MWriteStatement)

    def test_for_with_nested_if(self):
        """FOR with nested IF is properly structured."""
        parser = MUMPSParser()
        source = "TEST\tF I=1:1:10 I I#2 S X=I\n"
        routine = parser.parse(source)

        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        assert len(for_stmt.body.statements) == 1

        if_stmt = for_stmt.body.statements[0]
        assert isinstance(if_stmt, MIfStatement)
        assert len(if_stmt.then_scope.statements) == 1
        assert isinstance(if_stmt.then_scope.statements[0], MSetStatement)

    def test_if_with_nested_for(self):
        """IF with nested FOR is properly structured."""
        parser = MUMPSParser()
        source = "TEST\tI X>0 F I=1:1:X S A(I)=I\n"
        routine = parser.parse(source)

        if_stmt = routine.labels[0].body.statements[0]
        assert isinstance(if_stmt, MIfStatement)
        assert len(if_stmt.then_scope.statements) == 1

        for_stmt = if_stmt.then_scope.statements[0]
        assert isinstance(for_stmt, MForStatement)
        assert len(for_stmt.body.statements) == 1
        assert isinstance(for_stmt.body.statements[0], MSetStatement)


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestIfStatementAnalysis:
    """Tests for IF command analysis."""

    def test_if_with_condition(self):
        """IF X produces MIfStatement with condition."""
        stmt = analyze_first_command("I X")

        assert isinstance(stmt, MIfStatement)
        assert stmt.condition is not None

    def test_argumentless_if(self):
        """IF (argumentless) produces MIfStatement with no condition."""
        stmt = analyze_first_command("I")

        assert isinstance(stmt, MIfStatement)
        assert stmt.condition is None


@pytest.mark.asg
class TestParseIfCommand:
    """Test IF command parsing to full-fidelity ASG."""

    def test_simple_if(self):
        """I X=1 creates MIfStatement"""
        cmds = parse_commands_from_line("I X=1")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        # The condition is stored in both 'condition' and 'conditions'
        assert stmt.condition is not None
        assert len(stmt.conditions) == 1

    def test_argumentless_if(self):
        """I (uses $TEST) parses"""
        cmds = parse_commands_from_line("I")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert len(stmt.conditions) == 0


@pytest.mark.asg
class TestArgumentlessIfFollowedByCommand:
    """Test argumentless IF followed by another command (BUG-011 regression).

    In MUMPS, 'I  S X=1' (with TWO spaces after I) means:
    - Argumentless IF (checks $TEST)
    - Followed by SET command

    Single space 'I S' means IF with condition S (variable).
    """

    def test_argumentless_if_then_set(self):
        """I  S X=1 parses as argumentless IF + SET (not IF with condition S)."""
        cmds = parse_commands_from_line("I  S X=1")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "IfCommand"
        assert len(cmds[0].conditions) == 0  # argumentless
        assert cmds[1].__class__.__name__ == "SetCommand"

    def test_argumentless_if_then_quit(self):
        """I  Q parses as argumentless IF + QUIT."""
        cmds = parse_commands_from_line("I  Q")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "IfCommand"
        assert len(cmds[0].conditions) == 0
        assert cmds[1].__class__.__name__ == "QuitCommand"

    def test_argumentless_if_then_write(self):
        """I  W 1 parses as argumentless IF + WRITE."""
        cmds = parse_commands_from_line("I  W 1")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "IfCommand"
        assert len(cmds[0].conditions) == 0
        assert cmds[1].__class__.__name__ == "WriteCommand"

    def test_if_with_condition_single_space(self):
        """I S (single space) parses as IF with condition S."""
        cmds = parse_commands_from_line("I S")
        assert len(cmds) == 1
        assert cmds[0].__class__.__name__ == "IfCommand"
        assert len(cmds[0].conditions) == 1  # has condition

    def test_if_with_condition_then_set(self):
        """I 1 S X=1 parses as IF with condition 1, then SET."""
        cmds = parse_commands_from_line("I 1 S X=1")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "IfCommand"
        assert len(cmds[0].conditions) == 1
        assert cmds[1].__class__.__name__ == "SetCommand"


@pytest.mark.asg
class TestIfCommaConditions:
    """Tests for IF with comma-separated conditions.

    MUMPS allows comma-separated conditions in IF which act as AND:
        IF cond1,cond2  is equivalent to  IF cond1 IF cond2

    Reference: https://71.174.62.16/Demo/AnnoStd (MDC 8.1.35 IF Command)
    "IF with n arguments is equivalent in execution to n IFs, each
    with one argument, with the respective arguments in the same order."
    """

    def test_if_single_condition(self):
        """IF with single condition should parse."""
        commands = parse_commands_from_line("I X=1")
        assert len(commands) == 1
        assert commands[0].__class__.__name__ == "IfCommand"

    def test_if_two_conditions(self):
        """IF with two comma-separated conditions should parse."""
        commands = parse_commands_from_line("I I=2,J=2")
        assert len(commands) == 1, f"Expected 1 command, got {len(commands)}"
        assert commands[0].__class__.__name__ == "IfCommand"

    def test_if_three_conditions(self):
        """IF with three comma-separated conditions should parse."""
        commands = parse_commands_from_line("I A=1,B=2,C=3")
        assert len(commands) == 1
        assert commands[0].__class__.__name__ == "IfCommand"

    def test_if_conditions_with_expressions(self):
        """IF with complex conditions should parse."""
        commands = parse_commands_from_line('I X>0,Y<10,Z\'=""')
        assert len(commands) == 1
        assert commands[0].__class__.__name__ == "IfCommand"

    def test_if_conditions_in_line_with_other_commands(self):
        """IF with conditions in a line with FOR and SET should parse all commands."""
        commands = parse_commands_from_line('F I=1:1:3 S V=I I I=2,J=2 S V="X"')
        # Expected: FOR, SET, IF, SET
        assert len(commands) >= 3, (
            f"Expected at least 3 commands, got {len(commands)}: {[c.__class__.__name__ for c in commands]}"
        )

    def test_if_semantic_analysis(self):
        """IF with comma conditions should create proper ASG."""
        commands = parse_commands_from_line("I A=1,B=2")
        assert len(commands) == 1

        analyzer = SemanticAnalyzer()
        stmt = analyzer.analyze(commands[0], None)

        assert isinstance(stmt, MIfStatement)
        # Should have a list of conditions
        assert hasattr(stmt, "conditions") and stmt.conditions is not None, (
            "MIfStatement should have conditions list"
        )
        assert len(stmt.conditions) == 2, (
            f"Expected 2 conditions, got {len(stmt.conditions)}"
        )


@pytest.mark.asg
class TestV1BRLine37:
    """Regression test for V1BR.m line 37 parsing."""

    def test_v1br_line37_parses(self):
        """The problematic line from V1BR.m should parse with all commands."""
        # V1BR.m line 37 (label 170):
        # F I=1:1:3 F J=1:1:3 S V=V_I_J_" " I I=2,J=2 S V=V_"$" W !!,"TEST 6: *BREAK*" B  S V=V_"! "
        line = 'F I=1:1:3 F J=1:1:3 S V=V_I_J_" " I I=2,J=2 S V=V_"$" W !!,"TEST 6: *BREAK*" B  S V=V_"! "'

        commands = parse_commands_from_line(line)

        # Should have: FOR, FOR, SET, IF, SET, WRITE, BREAK, SET
        command_names = [c.__class__.__name__ for c in commands]
        assert len(commands) == 8, (
            f"Expected 8 commands, got {len(commands)}: {command_names}"
        )

        # Verify command types in order
        expected_types = [
            "ForCommand",
            "ForCommand",
            "SetCommand",
            "IfCommand",
            "SetCommand",
            "WriteCommand",
            "BreakCommand",
            "SetCommand",
        ]
        assert command_names == expected_types, (
            f"Expected {expected_types}, got {command_names}"
        )
