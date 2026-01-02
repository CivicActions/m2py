"""Tests for parser error handling (SC-007) and error collection.

Reference: M2PY Parser architecture
Migrated from:
- tests/unit/test_parser.py::TestParserErrorHandling
- tests/unit/test_parser.py::TestParseErrorCollection

SC-007: Syntax errors must include line and column numbers.
"""

import pytest

from m2py.parser import MUMPSParser, MUMPSSyntaxError
from m2py.asg import MParseError


@pytest.mark.parser
class TestParserErrorHandling:
    """Test parser error handling meets SC-007 requirements.

    SC-007: Syntax errors must include line and column numbers.

    Migrated from: tests/unit/test_parser.py::TestParserErrorHandling
    """

    def test_syntax_error_has_line_info(self):
        """T336: MUMPSSyntaxError should include line number."""
        parser = MUMPSParser()

        # Invalid syntax - null character triggers syntax error
        invalid_source = "\x00INVALID\n"

        with pytest.raises(MUMPSSyntaxError) as excinfo:
            parser.parse(invalid_source)

        # Error message should contain position info
        error_msg = str(excinfo.value)
        assert (
            "1:" in error_msg or "line" in error_msg.lower() or "Expected" in error_msg
        )

    def test_syntax_error_extracts_line_column_from_textx(self):
        """Phase 69: MUMPSSyntaxError should extract line/column from textX exceptions."""
        parser = MUMPSParser()

        # Invalid syntax - null character triggers TextXSyntaxError
        invalid_source = "\x00INVALID\n"

        with pytest.raises(MUMPSSyntaxError) as excinfo:
            parser.parse(invalid_source)

        # Line and column should be populated from the textX exception
        error = excinfo.value
        assert error.line is not None, "line should be extracted from TextXSyntaxError"
        assert error.line >= 1, "line should be a valid line number"
        # Column may be None for some errors, but if present should be valid
        if error.column is not None:
            assert error.column >= 0, "column should be a valid column number"

    def test_syntax_error_preserves_message(self):
        """T336: MUMPSSyntaxError should preserve original error message."""
        parser = MUMPSParser()

        # Invalid syntax - null character
        invalid_source = "\x00INVALID\n"

        with pytest.raises(MUMPSSyntaxError) as excinfo:
            parser.parse(invalid_source)

        # Should have meaningful error info
        assert excinfo.value.message is not None
        assert len(str(excinfo.value)) > 0

    def test_syntax_error_from_file_includes_filename(self):
        """T336: Errors from parse should include filename when provided."""
        parser = MUMPSParser()

        # Invalid syntax - null character triggers syntax error
        with pytest.raises(MUMPSSyntaxError) as excinfo:
            parser.parse("\x00INVALID\n", filename="/path/to/test.m")

        # Error should reference the file
        assert excinfo.value.source_file is not None
        assert "test.m" in excinfo.value.source_file or "test.m" in str(excinfo.value)

    def test_mumpssyntaxerror_attributes(self):
        """T336: MUMPSSyntaxError should have line/column attributes."""
        error = MUMPSSyntaxError(
            message="Test error",
            line=10,
            column=5,
            source_file="test.m",
            source_line="\tS X=1",
        )

        assert error.line == 10
        assert error.column == 5
        assert error.source_file == "test.m"
        assert error.source_line == "\tS X=1"

        # Message should include location
        error_str = str(error)
        assert "10" in error_str
        assert "5" in error_str
        assert "test.m" in error_str


@pytest.mark.parser
class TestParseErrorCollection:
    """Test parse error collection for error-tolerant parsing.

    Phase 94: Parser should collect parse errors in routine.parse_errors
    instead of silently dropping unparseable lines.

    Migrated from: tests/unit/test_parser.py::TestParseErrorCollection
    """

    def test_parse_error_collection_single_invalid_line(self):
        """T94.5: Single invalid line should be collected in parse_errors."""
        parser = MUMPSParser()
        # Valid label with invalid command syntax in continuation
        source = """LABEL
\tINVALIDZZ!@#$%^&*
"""
        routine = parser.parse(source)

        # Should have collected the error
        assert len(routine.parse_errors) >= 1
        assert isinstance(routine.parse_errors[0], MParseError)
        assert "INVALIDZZ" in routine.parse_errors[0].line_content

    def test_parse_error_collection_preserves_valid_lines(self):
        """T94.5: Valid lines should still be parsed when mixed with invalid."""
        parser = MUMPSParser()
        source = """LABEL S X=1
\tINVALIDZZ!@#$%^&*
\tS Y=2
"""
        routine = parser.parse(source)

        # Should have the valid statements
        label = routine.labels[0]
        # First line has S X=1, continuation has S Y=2 (skipping invalid line)
        stmt_count = len(label.body.statements)
        assert stmt_count == 2, (
            f"Expected 2 statements (before and after error), got {stmt_count}"
        )

        # Should have collected the error
        assert len(routine.parse_errors) >= 1

    def test_parse_error_collection_multiple_errors(self):
        """T94.5: Multiple invalid lines should all be collected."""
        parser = MUMPSParser()
        source = """LABEL S X=1
\tINVALID1!@#
\tS Y=2
\tINVALID2!@#
\tS Z=3
"""
        routine = parser.parse(source)

        # Should have collected both errors
        assert len(routine.parse_errors) >= 2

    def test_parse_error_has_line_number(self):
        """T94.5: Parse errors should include line number information."""
        parser = MUMPSParser()
        source = """LABEL S X=1
\tS Y=2
\tINVALIDZZ!@#$%^&*
\tS Z=3
"""
        routine = parser.parse(source)

        assert len(routine.parse_errors) >= 1
        error = routine.parse_errors[0]
        assert isinstance(error, MParseError)
        # The invalid line is on line 3
        assert error.line_number == 3

    def test_parse_error_str_representation(self):
        """T94.5: MParseError should have useful string representation."""
        error = MParseError(
            line_number=10, column=5, message="Unexpected token", line_content="BADLINE"
        )
        error_str = str(error)

        assert "10" in error_str
        assert "5" in error_str
        assert "Unexpected token" in error_str or "Parse error" in error_str
