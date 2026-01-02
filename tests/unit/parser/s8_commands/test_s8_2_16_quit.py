"""Tests for QUIT command parsing (§8.2.16).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.16

Migrated from:
- tests/unit/test_command_grammar.py
- tests/unit/test_line_parser.py::TestParseQuitCommand
- tests/unit/test_quit_then_command.py::TestQuitThenCommand
- tests/unit/test_quit_then_command.py::TestV1CALL1Line3
"""

import pytest

from m2py.analysis import analyze_command
from m2py.parser.line_parser import parse_commands_from_line


@pytest.mark.parser
class TestQuitCommandParsing:
    """Parser-level tests for QUIT command (§8.2.16)."""

    def test_simple_quit(self, command_metamodel):
        """Q - argumentless QUIT (§8.2.16)."""
        model = command_metamodel.model_from_str("Q", "QuitCommand")
        assert model.value is None

    def test_quit_with_value(self, command_metamodel):
        """Q X+Y - QUIT with return value (§8.2.16)."""
        model = command_metamodel.model_from_str("Q X+Y", "QuitCommand")
        assert model.value is not None

    def test_quit_conditional(self, command_metamodel):
        """Q:DONE - QUIT with postcondition (§8.2.16)."""
        model = command_metamodel.model_from_str("Q:DONE", "QuitCommand")
        assert model.postcond is not None


@pytest.mark.parser
class TestQuitFollowedBySet:
    """Tests for QUIT followed by SET - regression tests for T578 bug fix (§8.2.16)."""

    def test_quit_then_set_with_left_hand_piece(self):
        """Q S $P(X,';')=1 - regression test for T578 bug (§8.2.16)."""
        cmds = parse_commands_from_line('Q S $P(X,";")=1')
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[1].__class__.__name__ == "SetCommand"

    def test_quit_postcond_then_set_with_left_hand_piece(self):
        """Q:A='' S $P(X,';')=1 - regression test for T578 bug (§8.2.16)."""
        cmds = parse_commands_from_line('Q:A="" S $P(X,";")=1')
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[0].postcond is not None
        assert cmds[1].__class__.__name__ == "SetCommand"

    def test_for_quit_postcond_set_left_hand_piece(self):
        """F I=1:1 Q:A='' S $P(X,';')=1 - regression test for T578 bug full pattern (§8.2.16)."""
        cmds = parse_commands_from_line('F I=1:1 Q:A="" S $P(X,";")=1')
        assert len(cmds) == 3
        assert cmds[0].__class__.__name__ == "ForCommand"
        assert cmds[1].__class__.__name__ == "QuitCommand"
        assert cmds[2].__class__.__name__ == "SetCommand"

    def test_vv2lhp2_line73_full(self):
        """Full line 73 from VV2LHP2.m - the original failing case (§8.2.16)."""
        line = 'F I=1:1 S A=$T(TEX+I),X=Y Q:A=""  S $P(X,$P(A,";",2),$P(A,";",3),$P(A,";",4))=$P(A,";",5),VCOMP=VCOMP_X_" "'
        cmds = parse_commands_from_line(line)
        assert len(cmds) == 4
        assert cmds[0].__class__.__name__ == "ForCommand"
        assert cmds[1].__class__.__name__ == "SetCommand"
        assert cmds[2].__class__.__name__ == "QuitCommand"
        assert cmds[3].__class__.__name__ == "SetCommand"


@pytest.mark.parser
class TestQuitFollowedByTransaction:
    """Tests for QUIT followed by transaction commands - T96.11 (§8.2.16)."""

    def test_quit_then_tstart(self):
        """Q TS - QUIT followed by TSTART abbreviated (§8.2.16)."""
        cmds = parse_commands_from_line("Q TS")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[0].value is None  # Q has no return value
        assert cmds[1].__class__.__name__ == "TStartCommand"

    def test_quit_then_tstart_full(self):
        """Q TSTART - QUIT followed by TSTART full keyword (§8.2.16)."""
        cmds = parse_commands_from_line("Q TSTART")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[1].__class__.__name__ == "TStartCommand"

    def test_quit_then_tcommit(self):
        """Q TC - QUIT followed by TCOMMIT abbreviated (§8.2.16)."""
        cmds = parse_commands_from_line("Q TC")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[1].__class__.__name__ == "TCommitCommand"

    def test_quit_then_trestart(self):
        """Q TRE - QUIT followed by TRESTART abbreviated (§8.2.16)."""
        cmds = parse_commands_from_line("Q TRE")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[1].__class__.__name__ == "TRestartCommand"

    def test_quit_then_trollback(self):
        """Q TRO - QUIT followed by TROLLBACK abbreviated (§8.2.16)."""
        cmds = parse_commands_from_line("Q TRO")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[1].__class__.__name__ == "TRollbackCommand"


@pytest.mark.parser
class TestParseQuitCommand:
    """Test QUIT command parsing to full-fidelity ASG.

    Migrated from: tests/unit/test_line_parser.py::TestParseQuitCommand
    """

    def test_simple_quit(self):
        """Q creates MQuitStatement."""
        cmds = parse_commands_from_line("Q")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert stmt.return_value is None

    def test_quit_with_value(self):
        """Q X+1 parses return value."""
        cmds = parse_commands_from_line("Q X")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        # Return value should be captured as ASG node
        assert stmt.return_value is not None


# =============================================================================
# QUIT Then Command Tests
# =============================================================================


@pytest.mark.parser
class TestQuitThenCommand:
    """Tests for QUIT followed by another command (§8.2.16).

    MUMPS allows QUIT followed by another command on the same line:
        S X=1 Q  S Y=2    is SET, QUIT, SET

    The challenge is distinguishing:
        Q X       (QUIT with return value X)
        Q  S X=1  (QUIT then SET)

    Migrated from: tests/unit/test_quit_then_command.py::TestQuitThenCommand
    """

    def test_quit_alone(self):
        """Simple QUIT should parse (§8.2.16).

        Migrated from: tests/unit/test_quit_then_command.py::TestQuitThenCommand
        """
        commands = parse_commands_from_line("Q")
        assert len(commands) == 1
        assert commands[0].__class__.__name__ == "QuitCommand"

    def test_quit_with_return_value(self):
        """QUIT with return value should parse (§8.2.16).

        Migrated from: tests/unit/test_quit_then_command.py::TestQuitThenCommand
        """
        commands = parse_commands_from_line("Q X")
        assert len(commands) == 1
        assert commands[0].__class__.__name__ == "QuitCommand"
        assert hasattr(commands[0], "value") and commands[0].value is not None

    def test_quit_then_set(self):
        """QUIT followed by SET should parse as two commands (§8.2.16).

        Migrated from: tests/unit/test_quit_then_command.py::TestQuitThenCommand
        """
        commands = parse_commands_from_line("Q  S X=1")
        command_names = [c.__class__.__name__ for c in commands]
        assert len(commands) == 2, (
            f"Expected 2 commands, got {len(commands)}: {command_names}"
        )
        assert commands[0].__class__.__name__ == "QuitCommand"
        assert commands[1].__class__.__name__ == "SetCommand"

    def test_set_quit_set(self):
        """SET, QUIT, SET on same line should parse as three commands (§8.2.16).

        Migrated from: tests/unit/test_quit_then_command.py::TestQuitThenCommand
        """
        commands = parse_commands_from_line("S X=1 Q  S Y=2")
        command_names = [c.__class__.__name__ for c in commands]
        assert len(commands) == 3, (
            f"Expected 3 commands, got {len(commands)}: {command_names}"
        )
        assert commands[0].__class__.__name__ == "SetCommand"
        assert commands[1].__class__.__name__ == "QuitCommand"
        assert commands[2].__class__.__name__ == "SetCommand"

    def test_quit_before_command_keywords(self):
        """QUIT should not consume command keywords as return value (§8.2.16).

        Migrated from: tests/unit/test_quit_then_command.py::TestQuitThenCommand
        """
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


@pytest.mark.parser
class TestV1CALL1Line3:
    """Regression test for V1CALL1.m line 3 parsing (§8.2.16).

    Migrated from: tests/unit/test_quit_then_command.py::TestV1CALL1Line3
    """

    def test_v1call1_line3_parses_correctly(self):
        """V1CALL1.m line 3 should parse SET, QUIT, SET (not SET, QUIT, VIEW) (§8.2.16).

        Migrated from: tests/unit/test_quit_then_command.py::TestV1CALL1Line3
        """
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
        """V1CALL1.m line 3 should create proper ASG nodes (§8.2.16).

        Migrated from: tests/unit/test_quit_then_command.py::TestV1CALL1Line3
        """
        from m2py.asg.statements import MSetStatement, MQuitStatement

        line = 'S VCOMP=VCOMP_"1 " Q  S VCOMP=VCOMP_"QUIT ERROR"'

        commands = parse_commands_from_line(line)
        assert len(commands) == 3

        stmt1 = analyze_command(commands[0])
        stmt2 = analyze_command(commands[1])
        stmt3 = analyze_command(commands[2])

        assert isinstance(stmt1, MSetStatement)
        assert isinstance(stmt2, MQuitStatement)
        assert isinstance(stmt3, MSetStatement)
