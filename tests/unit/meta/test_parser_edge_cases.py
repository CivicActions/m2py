"""Tests for parser edge cases and miscellaneous grammar fixes.

These tests cover edge cases found in YottaDB test suites that required
grammar enhancements, as well as meta-level parser behavior tests.
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for parser edge case tests."""
    grammar_dir = (
        Path(__file__).parent.parent.parent.parent / "src" / "m2py" / "grammar"
    )
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


@pytest.mark.parser
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


@pytest.mark.parser
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


@pytest.mark.parser
class TestFunctionArgsEmpty:
    """Tests for function arguments with empty positions (Phase 103)."""

    def test_do_with_empty_first_arg(self, command_metamodel):
        """DO routine(,begin) - empty first argument"""
        model = command_metamodel.model_from_str(
            "DO select^routine(,begin)", "DoCommand"
        )
        assert model is not None

    def test_do_with_multiple_empty_args(self, command_metamodel):
        """DO routine(,,,val) - multiple empty positions"""
        model = command_metamodel.model_from_str("DO routine(,,,val)", "DoCommand")
        assert model is not None

    def test_extrinsic_with_empty_first_arg(self, command_metamodel):
        """$$func(,arg) - extrinsic with empty first"""
        model = command_metamodel.model_from_str("S X=$$func(,arg)", "SetCommand")
        assert model is not None
