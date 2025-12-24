"""Tests for IF command with comma-separated conditions (Issue #1).

MUMPS allows comma-separated conditions in IF which act as AND:
    IF cond1,cond2  is equivalent to  IF cond1 IF cond2

Reference: https://71.174.62.16/Demo/AnnoStd (MDC 8.1.35 IF Command)
"IF with n arguments is equivalent in execution to n IFs, each
with one argument, with the respective arguments in the same order."
"""

from m2py.analysis.command_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import SemanticAnalyzer
from m2py.asg.statements import MIfStatement


class TestIfCommaConditions:
    """Tests for IF with comma-separated conditions."""

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
