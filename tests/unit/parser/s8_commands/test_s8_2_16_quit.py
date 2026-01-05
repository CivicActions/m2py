"""Tests for QUIT command parsing (§8.2.16).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.16
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
class TestQuitCommandParsing:
    """Parser-level tests for QUIT command (§8.2.16)."""

    def test_quit_argumentless(self, command_metamodel):
        """Q parses argumentless QUIT (§8.2.16)."""
        model = command_metamodel.model_from_str("Q", "QuitCommand")
        assert model.value is None

    def test_quit_with_value(self, command_metamodel):
        """Q 1 parses QUIT with return value (§8.2.16)."""
        model = command_metamodel.model_from_str("Q 1", "QuitCommand")
        assert model.value is not None

    def test_quit_abbreviated(self, command_metamodel):
        """Q parses abbreviated form (§8.2.16)."""
        model = command_metamodel.model_from_str("Q", "QuitCommand")
        assert model.value is None

    def test_quit_with_postcondition(self, command_metamodel):
        """Q:condition parses correctly (§8.2.16)."""
        model = command_metamodel.model_from_str("Q:X", "QuitCommand")
        assert model.postcond is not None
        assert model.value is None

    def test_quit_followed_by_command(self, command_metamodel):
        """Q followed by another command on same line parses correctly (§8.2.16)."""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line("Q W 1")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[1].__class__.__name__ == "WriteCommand"

    def test_quit_with_string_value(self, command_metamodel):
        """Q "result" parses QUIT with string return value (§8.2.16)."""
        model = command_metamodel.model_from_str('Q "result"', "QuitCommand")
        assert model.value is not None

    def test_quit_with_expression(self, command_metamodel):
        """Q X+1 parses QUIT with expression return value (§8.2.16)."""
        model = command_metamodel.model_from_str("Q X+1", "QuitCommand")
        assert model.value is not None


@pytest.mark.parser
class TestQuitFollowedBySetParsing:
    """Parser-level tests for QUIT followed by SET command (§8.2.16)."""

    def test_quit_then_set_with_left_hand_piece(self):
        """Q S $P(X,';')=1 - regression test for T578 bug (§8.2.16)."""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line('Q S $P(X,";")=1')
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[1].__class__.__name__ == "SetCommand"

    def test_quit_postcond_then_set_with_left_hand_piece(self):
        """Q:A='' S $P(X,';')=1 - regression test for T578 bug (§8.2.16)."""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line('Q:A="" S $P(X,";")=1')
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[0].postcond is not None
        assert cmds[1].__class__.__name__ == "SetCommand"

    def test_for_quit_postcond_set_left_hand_piece(self):
        """F I=1:1 Q:A='' S $P(X,';')=1 - regression test for T578 bug (full pattern) (§8.2.16)."""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line('F I=1:1 Q:A="" S $P(X,";")=1')
        assert len(cmds) == 3
        assert cmds[0].__class__.__name__ == "ForCommand"
        assert cmds[1].__class__.__name__ == "QuitCommand"
        assert cmds[2].__class__.__name__ == "SetCommand"

    def test_vv2lhp2_line73_full(self):
        """Full line 73 from VV2LHP2.m - the original failing case (§8.2.16)."""
        from m2py.parser.line_parser import parse_commands_from_line

        line = 'F I=1:1 S A=$T(TEX+I),X=Y Q:A=""  S $P(X,$P(A,";",2),$P(A,";",3),$P(A,";",4))=$P(A,";",5),VCOMP=VCOMP_X_" "'
        cmds = parse_commands_from_line(line)
        assert len(cmds) == 4
        assert cmds[0].__class__.__name__ == "ForCommand"
        assert cmds[1].__class__.__name__ == "SetCommand"
        assert cmds[2].__class__.__name__ == "QuitCommand"
        assert cmds[3].__class__.__name__ == "SetCommand"


@pytest.mark.parser
class TestQuitFollowedByTransactionParsing:
    """Parser-level tests for QUIT followed by transaction commands (§8.2.16)."""

    def test_quit_then_tstart(self):
        """Q TS - QUIT followed by TSTART (abbreviated) (§8.2.16)."""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line("Q TS")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[0].value is None  # Q has no return value
        assert cmds[1].__class__.__name__ == "TStartCommand"

    def test_quit_then_tstart_full(self):
        """Q TSTART - QUIT followed by TSTART (full keyword) (§8.2.16)."""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line("Q TSTART")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[1].__class__.__name__ == "TStartCommand"

    def test_quit_then_tcommit(self):
        """Q TC - QUIT followed by TCOMMIT (abbreviated) (§8.2.16)."""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line("Q TC")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[1].__class__.__name__ == "TCommitCommand"

    def test_quit_then_trestart(self):
        """Q TRE - QUIT followed by TRESTART (abbreviated) (§8.2.16)."""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line("Q TRE")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[1].__class__.__name__ == "TRestartCommand"

    def test_quit_then_trollback(self):
        """Q TRO - QUIT followed by TROLLBACK (abbreviated) (§8.2.16)."""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line("Q TRO")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[1].__class__.__name__ == "TRollbackCommand"

    def test_trollback_then_set(self):
        """TRO S X=1 - TROLLBACK followed by SET (must not consume S as arg) (§8.2.16)."""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line("TRO S X=1")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "TRollbackCommand"
        assert cmds[1].__class__.__name__ == "SetCommand"

    def test_trollback_with_level(self):
        """TRO 1 - TROLLBACK with level (§8.2.16)."""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line("TRO 1")
        assert len(cmds) == 1
        assert cmds[0].__class__.__name__ == "TRollbackCommand"
        assert cmds[0].level is not None

    def test_quit_postcond_then_tstart(self):
        """Q:DONE TS - postconditioned QUIT then TSTART (§8.2.16)."""
        from m2py.parser.line_parser import parse_commands_from_line

        cmds = parse_commands_from_line("Q:DONE TS")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "QuitCommand"
        assert cmds[0].postcond is not None
        assert cmds[1].__class__.__name__ == "TStartCommand"
