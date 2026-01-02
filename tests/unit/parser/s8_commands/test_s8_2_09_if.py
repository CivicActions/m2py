"""Tests for IF command parsing (§8.2.9).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.9

Migrated from:
- tests/unit/test_grammar.py::TestSimpleIfGrammar
- tests/unit/test_line_parser.py::TestParseIfCommand
- tests/unit/test_line_parser.py::TestArgumentlessIfFollowedByCommand
- tests/unit/test_parser.py::TestControlFlowBodyPopulation (IF/ELSE tests)
- tests/unit/test_if_comma_conditions.py::TestIfCommaConditions
- tests/unit/test_if_comma_conditions.py::TestV1BRLine37
"""

import pytest

from m2py.asg import MRoutine
from m2py.analysis import analyze_command
from m2py.parser import MUMPSParser
from m2py.parser.line_parser import parse_commands_from_line


@pytest.mark.parser
class TestIfCommandParsing:
    """Parser-level tests for IF command (§8.2.9)."""

    def test_simple_if(self, command_metamodel):
        """I X=1 - abbreviated IF with condition (§8.2.9)."""
        model = command_metamodel.model_from_str("I X=1", "IfCommand")
        assert model.conditions is not None
        assert len(model.conditions) == 1

    def test_if_full_keyword(self, command_metamodel):
        """IF X=1 - full keyword with condition (§8.2.9)."""
        model = command_metamodel.model_from_str("IF X=1", "IfCommand")
        assert model.conditions is not None
        assert len(model.conditions) == 1

    def test_argumentless_if(self, command_metamodel):
        """I - argumentless IF uses $TEST (§8.2.9)."""
        model = command_metamodel.model_from_str("I", "IfCommand")
        assert len(model.conditions) == 0


@pytest.mark.parser
class TestSimpleIfGrammar:
    """Test simple IF command parsing full-routine acceptance (§8.2.9).

    Migrated from: tests/unit/test_grammar.py::TestSimpleIfGrammar
    """

    def test_simple_if(self):
        """IF with single condition (§8.2.9)."""
        parser = MUMPSParser()
        source = "LABEL\tI X=1 W X\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_if_abbreviated(self):
        """I abbreviation should work same as IF (§8.2.9)."""
        parser = MUMPSParser()
        source = "LABEL\tI Y W Y\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_if_comparison(self):
        """IF with comparison operator (§8.2.9)."""
        parser = MUMPSParser()
        source = 'LABEL\tI A>B W "A is greater"\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_if_argumentless(self):
        """IF without explicit condition (uses $T) (§8.2.9)."""
        parser = MUMPSParser()
        source = "LABEL\tI  W $T\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestParseIfCommand:
    """Test IF command parsing to full-fidelity ASG.

    Migrated from: tests/unit/test_line_parser.py::TestParseIfCommand
    """

    def test_simple_if(self):
        """I X=1 creates MIfStatement."""
        cmds = parse_commands_from_line("I X=1")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        # The condition is stored in both 'condition' and 'conditions'
        assert stmt.condition is not None
        assert len(stmt.conditions) == 1

    def test_argumentless_if(self):
        """I (uses $TEST) parses."""
        cmds = parse_commands_from_line("I")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert len(stmt.conditions) == 0


@pytest.mark.parser
class TestArgumentlessIfFollowedByCommand:
    """Test argumentless IF followed by another command (BUG-011 regression).

    In MUMPS, 'I  S X=1' (with TWO spaces after I) means:
    - Argumentless IF (checks $TEST)
    - Followed by SET command

    Single space 'I S' means IF with condition S (variable).

    Migrated from: tests/unit/test_line_parser.py::TestArgumentlessIfFollowedByCommand
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


# =============================================================================
# Phase 12: Control Flow Body Population Tests
# =============================================================================


@pytest.mark.parser
class TestIfBodyPopulation:
    """T348-T355: Tests for IF/ELSE body population.

    These tests verify that IF and ELSE block bodies are properly populated
    with following commands.

    Migrated from: tests/unit/test_parser.py::TestControlFlowBodyPopulation
    """

    def test_if_body_single_command(self):
        """T348: IF captures single following command in then_scope."""
        from m2py.asg.statements import MIfStatement, MSetStatement

        parser = MUMPSParser()
        source = "TEST\tI X=1 S Y=2\n"
        routine = parser.parse(source)

        if_stmt = routine.labels[0].body.statements[0]
        assert isinstance(if_stmt, MIfStatement)
        assert len(if_stmt.then_scope.statements) == 1
        assert isinstance(if_stmt.then_scope.statements[0], MSetStatement)

    def test_if_body_multiple_commands(self):
        """T348: IF captures multiple following commands in then_scope."""
        from m2py.asg.statements import MIfStatement, MSetStatement, MWriteStatement

        parser = MUMPSParser()
        source = "TEST\tI X=1 S Y=2 W Y\n"
        routine = parser.parse(source)

        if_stmt = routine.labels[0].body.statements[0]
        assert isinstance(if_stmt, MIfStatement)
        assert len(if_stmt.then_scope.statements) == 2
        assert isinstance(if_stmt.then_scope.statements[0], MSetStatement)
        assert isinstance(if_stmt.then_scope.statements[1], MWriteStatement)

    def test_else_body_commands(self):
        """T348: ELSE captures following commands in body."""
        from m2py.asg.statements import MElseStatement, MSetStatement, MWriteStatement

        parser = MUMPSParser()
        source = "TEST\tE  S Y=3 W Y\n"
        routine = parser.parse(source)

        else_stmt = routine.labels[0].body.statements[0]
        assert isinstance(else_stmt, MElseStatement)
        assert len(else_stmt.body.statements) == 2
        assert isinstance(else_stmt.body.statements[0], MSetStatement)
        assert isinstance(else_stmt.body.statements[1], MWriteStatement)

    def test_if_with_nested_for(self):
        """T355: IF with nested FOR is properly structured."""
        from m2py.asg.statements import MIfStatement, MForStatement, MSetStatement

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


# =============================================================================
# Comma-Separated Conditions Tests
# =============================================================================


@pytest.mark.parser
class TestIfCommaConditions:
    """Tests for IF with comma-separated conditions (§8.2.9).

    MUMPS allows comma-separated conditions in IF which act as AND:
        IF cond1,cond2  is equivalent to  IF cond1 IF cond2

    Reference: https://71.174.62.16/Demo/AnnoStd (MDC 8.1.35 IF Command)

    Migrated from: tests/unit/test_if_comma_conditions.py::TestIfCommaConditions
    """

    def test_if_single_condition(self):
        """IF with single condition should parse (§8.2.9).

        Migrated from: tests/unit/test_if_comma_conditions.py::TestIfCommaConditions
        """
        commands = parse_commands_from_line("I X=1")
        assert len(commands) == 1
        assert commands[0].__class__.__name__ == "IfCommand"

    def test_if_two_conditions(self):
        """IF with two comma-separated conditions should parse (§8.2.9).

        Migrated from: tests/unit/test_if_comma_conditions.py::TestIfCommaConditions
        """
        commands = parse_commands_from_line("I I=2,J=2")
        assert len(commands) == 1, f"Expected 1 command, got {len(commands)}"
        assert commands[0].__class__.__name__ == "IfCommand"

    def test_if_three_conditions(self):
        """IF with three comma-separated conditions should parse (§8.2.9).

        Migrated from: tests/unit/test_if_comma_conditions.py::TestIfCommaConditions
        """
        commands = parse_commands_from_line("I A=1,B=2,C=3")
        assert len(commands) == 1
        assert commands[0].__class__.__name__ == "IfCommand"

    def test_if_conditions_with_expressions(self):
        """IF with complex conditions should parse (§8.2.9).

        Migrated from: tests/unit/test_if_comma_conditions.py::TestIfCommaConditions
        """
        commands = parse_commands_from_line('I X>0,Y<10,Z\'=""')
        assert len(commands) == 1
        assert commands[0].__class__.__name__ == "IfCommand"

    def test_if_conditions_in_line_with_other_commands(self):
        """IF with conditions in a line with FOR and SET should parse all commands (§8.2.9).

        Migrated from: tests/unit/test_if_comma_conditions.py::TestIfCommaConditions
        """
        commands = parse_commands_from_line('F I=1:1:3 S V=I I I=2,J=2 S V="X"')
        # Expected: FOR, SET, IF, SET
        assert len(commands) >= 3, (
            f"Expected at least 3 commands, got {len(commands)}: {[c.__class__.__name__ for c in commands]}"
        )

    def test_if_semantic_analysis(self):
        """IF with comma conditions should create proper ASG (§8.2.9).

        Migrated from: tests/unit/test_if_comma_conditions.py::TestIfCommaConditions
        """
        from m2py.asg.statements import MIfStatement

        commands = parse_commands_from_line("I A=1,B=2")
        assert len(commands) == 1

        stmt = analyze_command(commands[0])

        assert isinstance(stmt, MIfStatement)
        # Should have a list of conditions
        assert hasattr(stmt, "conditions") and stmt.conditions is not None, (
            "MIfStatement should have conditions list"
        )
        assert len(stmt.conditions) == 2, (
            f"Expected 2 conditions, got {len(stmt.conditions)}"
        )


@pytest.mark.parser
class TestV1BRLine37:
    """Regression test for V1BR.m line 37 parsing (§8.2.9).

    Migrated from: tests/unit/test_if_comma_conditions.py::TestV1BRLine37
    """

    def test_v1br_line37_parses(self):
        """The problematic line from V1BR.m should parse with all commands (§8.2.9).

        Migrated from: tests/unit/test_if_comma_conditions.py::TestV1BRLine37
        """
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
