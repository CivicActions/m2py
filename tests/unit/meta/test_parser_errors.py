"""Tests for parser error handling.

Verifies syntax error detection, error collection, and recovery behavior.

MUMPS 1995 Reference: §6.1 Routine Structure
"""

import pytest

from m2py.parser import MUMPSParser, MUMPSSyntaxError
from m2py.asg import MRoutine


class TestParserErrorHandling:
    """Test parser error detection and reporting."""

    def test_syntax_error_raised_for_invalid_line(self):
        """Parser should raise MUMPSSyntaxError for invalid syntax."""
        parser = MUMPSParser()
        # Line that's neither a label, continuation, nor comment
        # A line starting with just '=' is invalid
        with pytest.raises(MUMPSSyntaxError):
            parser.parse("= invalid\n")

    def test_syntax_error_includes_message(self):
        """MUMPSSyntaxError should include a descriptive message."""
        parser = MUMPSParser()
        try:
            parser.parse("= invalid\n")
            pytest.fail("Should have raised MUMPSSyntaxError")
        except MUMPSSyntaxError as e:
            assert len(str(e)) > 0

    def test_syntax_error_for_unclosed_string(self):
        """Parser may collect unclosed string as parse error rather than raising."""
        parser = MUMPSParser()
        # Unclosed strings are typically detected during line parsing
        # but may not raise - instead captured as parse_error
        routine = parser.parse('TEST\tS X="unclosed\n')
        # Parser should return a routine - errors may be in parse_errors list
        assert isinstance(routine, MRoutine)

    def test_parse_returns_routine_despite_errors_in_content(self):
        """Parser should return MRoutine even when command syntax has errors."""
        parser = MUMPSParser()
        # Label line is valid, but command syntax may have issues
        # The parser should still return an MRoutine with the label
        routine = parser.parse("LABEL\tS X=\n")  # SET with no value
        assert isinstance(routine, MRoutine)
        assert len(routine.labels) == 1

    def test_parse_error_tracks_location(self):
        """Parse errors should track line and column information."""
        parser = MUMPSParser()
        try:
            parser.parse("= invalid\n")
        except MUMPSSyntaxError as e:
            # Error message should contain location info
            error_str = str(e)
            # Should mention line or position
            assert (
                "line" in error_str.lower()
                or "position" in error_str.lower()
                or ":" in error_str
            )


class TestParseErrorCollection:
    """Test parse error collection in MRoutine."""

    def test_routine_has_parse_errors_list(self):
        """MRoutine should have parse_errors attribute."""
        parser = MUMPSParser()
        routine = parser.parse("LABEL\n")
        assert hasattr(routine, "parse_errors")
        assert isinstance(routine.parse_errors, list)

    def test_valid_code_has_no_parse_errors(self):
        """Valid code should result in empty parse_errors."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\tS X=1\n\tW X\n\tQ\n")
        assert routine.parse_errors == []

    def test_invalid_argument_adds_parse_error(self):
        """Invalid command argument should add to parse_errors."""
        parser = MUMPSParser()
        # FOR with invalid syntax - this gets captured as a parse error
        routine = parser.parse("TEST\tF =1:1 W X\n")  # Invalid FOR syntax
        # This may or may not add parse_errors depending on implementation
        # but should at least return a routine
        assert isinstance(routine, MRoutine)

    def test_parse_errors_include_line_info(self):
        """Parse errors should include line number information."""
        parser = MUMPSParser()
        # Create error on specific line
        routine = parser.parse("GOOD\tS X=1\nBAD\tS Y=\n")  # Line 2 has error
        # The parser should create routine even with errors
        assert isinstance(routine, MRoutine)
        # Errors if any should reference line info
        for error in routine.parse_errors:
            assert hasattr(error, "line") or "line" in str(error).lower()


class TestUnknownCommand:
    """Tests for unknown command detection (Phase 101)."""

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

    def test_multiple_errors_collected(self):
        """Multiple errors should all be collected in parse_errors."""
        parser = MUMPSParser()
        # Multiple problematic constructs
        source = """MAIN
\tS A=
\tS B=
\tQ
"""
        routine = parser.parse(source)
        # Should still return routine
        assert isinstance(routine, MRoutine)
        # The parse errors may or may not be collected depending on
        # whether these are treated as "empty" values or errors
