"""Tests for QUIT followed by command on same line (Issue #2).

MUMPS allows QUIT followed by another command on the same line:
    S X=1 Q  S Y=2    is SET, QUIT, SET

The challenge is distinguishing:
    Q X       (QUIT with return value X)
    Q  S X=1  (QUIT then SET)

Reference: MUMPS uses context-sensitive parsing where command keywords
after QUIT are recognized as new commands, not as return values.
"""

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import SemanticAnalyzer
from m2py.asg.statements import MSetStatement, MQuitStatement


class TestQuitThenCommand:
    """Tests for QUIT followed by another command."""

    def test_quit_alone(self):
        """Simple QUIT should parse."""
        commands = parse_commands_from_line("Q")
        assert len(commands) == 1
        assert commands[0].__class__.__name__ == "QuitCommand"

    def test_quit_with_value(self):
        """QUIT with return value should parse."""
        commands = parse_commands_from_line("Q X")
        assert len(commands) == 1
        assert commands[0].__class__.__name__ == "QuitCommand"
        assert hasattr(commands[0], "value") and commands[0].value is not None

    def test_quit_then_set(self):
        """QUIT followed by SET should parse as two commands."""
        commands = parse_commands_from_line("Q  S X=1")
        command_names = [c.__class__.__name__ for c in commands]
        assert len(commands) == 2, (
            f"Expected 2 commands, got {len(commands)}: {command_names}"
        )
        assert commands[0].__class__.__name__ == "QuitCommand"
        assert commands[1].__class__.__name__ == "SetCommand"

    def test_set_quit_set(self):
        """SET, QUIT, SET on same line should parse as three commands."""
        commands = parse_commands_from_line("S X=1 Q  S Y=2")
        command_names = [c.__class__.__name__ for c in commands]
        assert len(commands) == 3, (
            f"Expected 3 commands, got {len(commands)}: {command_names}"
        )
        assert commands[0].__class__.__name__ == "SetCommand"
        assert commands[1].__class__.__name__ == "QuitCommand"
        assert commands[2].__class__.__name__ == "SetCommand"

    def test_quit_before_command_keywords(self):
        """QUIT should not consume command keywords as return value."""
        # Q followed by various command abbreviations
        test_cases = [
            ("Q S X=1", 2, ["QuitCommand", "SetCommand"]),
            ("Q W X", 2, ["QuitCommand", "WriteCommand"]),
            ("Q R X", 2, ["QuitCommand", "ReadCommand"]),
            ("Q I X", 2, ["QuitCommand", "IfCommand"]),
            ("Q K X", 2, ["QuitCommand", "KillCommand"]),
        ]

        for line, expected_count, expected_types in test_cases:
            commands = parse_commands_from_line(line)
            command_names = [c.__class__.__name__ for c in commands]
            assert len(commands) == expected_count, (
                f"Line '{line}': expected {expected_count} commands, got {len(commands)}: {command_names}"
            )
            assert command_names == expected_types, (
                f"Line '{line}': expected {expected_types}, got {command_names}"
            )


class TestV1CALL1Line3:
    """Regression test for V1CALL1.m line 3 parsing."""

    def test_v1call1_line3_parses_correctly(self):
        """V1CALL1.m line 3 should parse SET, QUIT, SET (not SET, QUIT, VIEW)."""
        # Line 3 from V1CALL1.m:
        line = 'S VCOMP=VCOMP_"1 " Q  S VCOMP=VCOMP_"QUIT ERROR"'

        commands = parse_commands_from_line(line)
        command_names = [c.__class__.__name__ for c in commands]

        # Should have: SET, QUIT, SET
        assert len(commands) == 3, (
            f"Expected 3 commands, got {len(commands)}: {command_names}"
        )

        assert commands[0].__class__.__name__ == "SetCommand", (
            f"First command should be SetCommand, got {commands[0].__class__.__name__}"
        )
        assert commands[1].__class__.__name__ == "QuitCommand", (
            f"Second command should be QuitCommand, got {commands[1].__class__.__name__}"
        )
        assert commands[2].__class__.__name__ == "SetCommand", (
            f"Third command should be SetCommand, got {commands[2].__class__.__name__}"
        )

    def test_v1call1_line3_semantic_analysis(self):
        """V1CALL1.m line 3 should create proper ASG nodes."""
        line = 'S VCOMP=VCOMP_"1 " Q  S VCOMP=VCOMP_"QUIT ERROR"'

        commands = parse_commands_from_line(line)
        assert len(commands) == 3

        analyzer = SemanticAnalyzer()

        stmt1 = analyzer.analyze(commands[0], None)
        stmt2 = analyzer.analyze(commands[1], None)
        stmt3 = analyzer.analyze(commands[2], None)

        assert isinstance(stmt1, MSetStatement)
        assert isinstance(stmt2, MQuitStatement)
        assert isinstance(stmt3, MSetStatement)
