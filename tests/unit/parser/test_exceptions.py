"""Unit tests for parser exception classes.

Tests for MUMPSSyntaxError and MUMPSUnknownCommandError.
"""

import pytest

from m2py.parser.exceptions import MUMPSSyntaxError, MUMPSUnknownCommandError


# =============================================================================
# Tests for MUMPSSyntaxError
# =============================================================================


@pytest.mark.parser
class TestMUMPSSyntaxError:
    """Tests for MUMPSSyntaxError exception class."""

    def test_basic_message(self):
        """Error with just a message."""
        err = MUMPSSyntaxError("invalid syntax")
        assert "invalid syntax" in str(err)

    def test_with_line_number(self):
        """Error with line number."""
        err = MUMPSSyntaxError("invalid syntax", line=5)
        assert "line 5" in str(err)
        assert err.line == 5

    def test_with_column_number(self):
        """Error with column number."""
        err = MUMPSSyntaxError("invalid syntax", column=10)
        assert "column 10" in str(err)
        assert err.column == 10

    def test_with_source_file(self):
        """Error with source file."""
        err = MUMPSSyntaxError("invalid syntax", source_file="test.m")
        assert "test.m" in str(err)
        assert err.source_file == "test.m"

    def test_with_all_location_info(self):
        """Error with full location info."""
        err = MUMPSSyntaxError(
            "invalid syntax",
            line=5,
            column=10,
            source_file="test.m",
        )
        error_str = str(err)
        assert "test.m" in error_str
        assert "line 5" in error_str
        assert "column 10" in error_str

    def test_with_source_line(self):
        """Error with source line text."""
        err = MUMPSSyntaxError(
            "invalid syntax",
            line=1,
            column=5,
            source_line='TEST S X="bad',
        )
        error_str = str(err)
        assert 'TEST S X="bad' in error_str
        assert err.source_line == 'TEST S X="bad'

    def test_with_source_line_shows_caret(self):
        """Error with source line shows caret at column."""
        err = MUMPSSyntaxError(
            "invalid syntax",
            line=1,
            column=5,
            source_line="TEST S X=1",
        )
        error_str = str(err)
        # Should have caret pointing to column 5
        assert "^" in error_str
        # Caret should be after 4 spaces (column is 1-based)
        assert "    ^" in error_str

    def test_without_source_file_shows_unknown_location(self):
        """Error without location info shows 'unknown location'."""
        err = MUMPSSyntaxError("invalid syntax")
        assert "unknown location" in str(err)

    def test_source_line_without_column_no_caret(self):
        """Source line without column doesn't show caret."""
        err = MUMPSSyntaxError(
            "invalid syntax",
            source_line="TEST S X=1",
        )
        error_str = str(err)
        assert "TEST S X=1" in error_str
        # Without column, should not have caret line (just source line)
        lines = error_str.split("\n")
        # The last line with content should be the source line, not a caret
        assert not any("^" in line for line in lines)

    def test_column_zero_no_caret(self):
        """Column of 0 doesn't show caret (column is 1-based)."""
        err = MUMPSSyntaxError(
            "invalid syntax",
            line=1,
            column=0,
            source_line="TEST S X=1",
        )
        error_str = str(err)
        assert "TEST S X=1" in error_str
        # Column 0 is not > 0, so no caret
        assert "^" not in error_str


# =============================================================================
# Tests for MUMPSUnknownCommandError
# =============================================================================


@pytest.mark.parser
class TestMUMPSUnknownCommandError:
    """Tests for MUMPSUnknownCommandError exception class."""

    def test_basic_unknown_command(self):
        """Error for unknown command with just command name."""
        err = MUMPSUnknownCommandError("XYZ")
        assert "XYZ" in str(err)
        assert "Unknown command" in str(err)
        assert err.command == "XYZ"

    def test_with_location_info(self):
        """Error for unknown command with location info."""
        err = MUMPSUnknownCommandError(
            "XYZ",
            line=10,
            column=1,
            source_file="test.m",
        )
        error_str = str(err)
        assert "XYZ" in error_str
        assert "line 10" in error_str
        assert "test.m" in error_str

    def test_with_source_line(self):
        """Error for unknown command with source line."""
        err = MUMPSUnknownCommandError(
            "XYZ",
            line=1,
            column=6,
            source_line="TEST\tXYZ argument",
        )
        error_str = str(err)
        assert "XYZ argument" in error_str
        assert "^" in error_str

    def test_is_subclass_of_syntax_error(self):
        """MUMPSUnknownCommandError is a subclass of MUMPSSyntaxError."""
        err = MUMPSUnknownCommandError("XYZ")
        assert isinstance(err, MUMPSSyntaxError)

    def test_message_includes_helpful_text(self):
        """Error message includes helpful text about abbreviations."""
        err = MUMPSUnknownCommandError("XYZ")
        error_str = str(err)
        assert (
            "valid abbreviation" in error_str.lower()
            or "recognized" in error_str.lower()
        )
