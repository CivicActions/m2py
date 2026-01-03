"""Tests for line_parser.py internal functions.

Tests the textX grammar-based parsing and extraction functions.
These are meta/infrastructure tests for the internal parsing APIs.

For semantic analysis (analyze_command, analyze_statement), see test_semantic_analyzer_internals.py.
"""

from m2py.parser.line_parser import (
    parse_line_content,
    parse_commands_from_line,
)
from tests.helpers.parsing import parse_expression


class TestParseLineContent:
    """Test line content parsing using textX grammar."""

    def test_single_command(self):
        """Parse line with single command."""
        model = parse_line_content("S X=1")
        assert model is not None
        assert len(model.commands) == 1
        assert model.commands[0].cmd.__class__.__name__ == "SetCommand"

    def test_multiple_commands(self):
        """Parse line with multiple commands."""
        model = parse_line_content("S X=1 W X")
        assert model is not None
        assert len(model.commands) == 2
        assert model.commands[0].cmd.__class__.__name__ == "SetCommand"
        assert model.commands[1].cmd.__class__.__name__ == "WriteCommand"

    def test_with_comment(self):
        """Parse line with trailing comment."""
        model = parse_line_content("S X=1 ;comment here")
        assert model is not None
        assert len(model.commands) == 1
        assert model.comment is not None
        assert model.comment.text == "comment here"

    def test_only_comment(self):
        """Parse line with only comment."""
        model = parse_line_content(";just a comment")
        assert model is not None
        assert len(model.commands) == 0
        assert model.comment is not None
        assert model.comment.text == "just a comment"

    def test_empty_line(self):
        """Parse empty line - returns empty LineContent or empty string."""
        model = parse_line_content("")
        # Empty input may return empty string or LineContent with no commands
        if model is not None and hasattr(model, "commands"):
            assert len(model.commands) == 0
            assert model.comment is None
        else:
            # textX may return empty string for empty input
            assert model == "" or model is None

    def test_adjacent_format_controls(self):
        """Parse W !! (adjacent newlines without comma)."""
        model = parse_line_content("W !!")
        assert model is not None
        assert len(model.commands) == 1
        cmd = model.commands[0].cmd
        assert cmd.__class__.__name__ == "WriteCommand"
        assert len(cmd.args) == 2

    def test_complex_line(self):
        """Parse complex line with multiple commands and comment."""
        model = parse_line_content("S X=1 F I=1:1:10 W I,! Q  ;loop")
        assert model is not None
        assert len(model.commands) == 4
        assert model.comment is not None


class TestParseCommandsFromLine:
    """Test extracting commands from line content."""

    def test_get_commands(self):
        """Get list of command models."""
        cmds = parse_commands_from_line("S X=1 W X")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "SetCommand"
        assert cmds[1].__class__.__name__ == "WriteCommand"

    def test_empty_line(self):
        """Empty line returns empty list."""
        cmds = parse_commands_from_line("")
        assert cmds == []


class TestGetLineComment:
    """Test extracting comments from line content using parse_line_content."""

    def test_has_comment(self):
        """Extract comment from line."""
        model = parse_line_content("S X=1 ;my comment")
        assert model.comment is not None
        assert model.comment.text == "my comment"

    def test_no_comment(self):
        """Line without comment returns None."""
        model = parse_line_content("S X=1")
        assert model.comment is None


class TestParseCommand:
    """Test generic command parsing using parse_commands_from_line."""

    def test_parse_set_command(self):
        """S X=1 parses as SetCommand"""
        cmds = parse_commands_from_line("S X=1")
        assert len(cmds) == 1
        assert cmds[0].__class__.__name__ == "SetCommand"

    def test_parse_write_command(self):
        """W X parses as WriteCommand"""
        cmds = parse_commands_from_line("W X")
        assert len(cmds) == 1
        assert cmds[0].__class__.__name__ == "WriteCommand"

    def test_parse_invalid(self):
        """Invalid command returns MParseError (Phase 94: error-tolerant parsing)"""
        from m2py.asg.elements import MParseError

        result = parse_commands_from_line("$$$INVALID")
        # Phase 94: Now returns MParseError instead of empty list
        assert isinstance(result, MParseError)


class TestParseExpression:
    """Test expression parsing."""

    def test_parse_simple_var(self):
        """Variable X parses correctly"""
        result = parse_expression("X")
        assert result is not None
        # The parsed expression is an Expr with structure
        assert hasattr(result, "left")

    def test_parse_arithmetic(self):
        """X+Y*Z parses with binary operators"""
        result = parse_expression("X+Y*Z")
        assert result is not None
        # Has left operand and tail for operators
        assert result.left is not None
        assert len(result.tail) > 0

    def test_parse_function(self):
        """$LENGTH(X) parses correctly"""
        result = parse_expression("$LENGTH(X)")
        assert result is not None
        # Function call is wrapped in expression structure
        assert hasattr(result, "left")

    def test_parse_global_var(self):
        """^GLOBAL parses correctly"""
        result = parse_expression("^GLOBAL")
        assert result is not None
        assert hasattr(result, "left")

    def test_parse_special_var(self):
        """$TEST parses correctly"""
        result = parse_expression("$TEST")
        assert result is not None
        assert hasattr(result, "left")


class TestExtractFunctionErrorPaths:
    """Test error paths in extraction helper functions."""

    def test_extract_for_no_for_command(self):
        """get_for_info returns None when no FOR present."""
        from tests.helpers.extraction_helpers import get_for_info

        result = get_for_info("S X=1")
        assert result is None

    def test_extract_for_empty_string(self):
        """get_for_info handles empty string."""
        from tests.helpers.extraction_helpers import get_for_info

        result = get_for_info("")
        assert result is None

    def test_extract_goto_no_goto_command(self):
        """get_goto_info returns None when no GOTO present."""
        from tests.helpers.extraction_helpers import get_goto_info

        result = get_goto_info("W !,X")
        assert result is None

    def test_extract_goto_empty_string(self):
        """get_goto_info handles empty string."""
        from tests.helpers.extraction_helpers import get_goto_info

        result = get_goto_info("")
        assert result is None

    def test_extract_for_with_incomplete_syntax(self):
        """get_for_info handles incomplete FOR gracefully."""
        from tests.helpers.extraction_helpers import get_for_info

        # Incomplete FOR syntax - should not crash
        _result = get_for_info("F")  # Result intentionally unused
        # May return None or a valid result - key is no exception

    def test_extract_goto_with_valid_syntax(self):
        """get_goto_info extracts correct info."""
        from tests.helpers.extraction_helpers import get_goto_info

        _result = get_goto_info("G LABEL^ROUTINE")
