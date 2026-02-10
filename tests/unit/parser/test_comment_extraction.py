"""Tests for comment extraction from MUMPS source lines.

Tests the extract_comment() function in parser/line_parser.py and
verifies that comments are correctly populated on MStatement.comment
during parsing.
"""

import pytest

from m2py.parser.line_parser import extract_comment
from m2py.parser.parser import MUMPSParser


# =============================================================================
# Unit tests for extract_comment()
# =============================================================================


@pytest.mark.parser
class TestExtractComment:
    """Test extract_comment() utility function."""

    def test_simple_comment(self):
        """Semicolon followed by comment text."""
        assert extract_comment("SET X=1 ; this is a comment") == "this is a comment"

    def test_comment_no_space(self):
        """Semicolon without leading space."""
        assert extract_comment("SET X=1;comment") == "comment"

    def test_no_comment(self):
        """Line with no semicolon returns empty string."""
        assert extract_comment("SET X=1") == ""

    def test_empty_line(self):
        """Empty line returns empty string."""
        assert extract_comment("") == ""

    def test_semicolon_in_string_literal(self):
        """Semicolons inside quoted strings are NOT comment delimiters."""
        assert extract_comment('WRITE "hello;world"') == ""

    def test_semicolon_in_string_with_trailing_comment(self):
        """Semicolons in strings ignored, trailing comment extracted."""
        assert extract_comment('WRITE "hello;world" ; real comment') == "real comment"

    def test_comment_only(self):
        """Line that is just a comment."""
        assert extract_comment("; full line comment") == "full line comment"

    def test_comment_with_trailing_whitespace(self):
        """Trailing whitespace in comment is stripped."""
        assert extract_comment("SET X=1 ; comment   ") == "comment"

    def test_empty_comment(self):
        """Semicolon with no text after it."""
        assert extract_comment("SET X=1 ;") == ""

    def test_multiple_semicolons(self):
        """Only the first unquoted semicolon starts the comment."""
        assert extract_comment("SET X=1 ; first ; second") == "first ; second"

    def test_escaped_quotes(self):
        """MUMPS uses doubled quotes for escaping."""
        assert extract_comment('WRITE "say ""hello""" ; comment') == "comment"

    def test_nested_quotes_with_semicolons(self):
        """Multiple quoted strings with semicolons."""
        assert extract_comment('SET X="a;b",Y="c;d" ; end') == "end"


# =============================================================================
# Integration tests: comments populated on MStatement during parsing
# =============================================================================


@pytest.mark.parser
class TestCommentOnStatement:
    """Verify MStatement.comment is populated during parsing."""

    @pytest.fixture
    def parser(self):
        return MUMPSParser()

    def test_label_line_with_comment(self, parser):
        """Comment on a label line is attached to the first statement."""
        source = "TEST SET X=1 ; my comment\n"
        routine = parser.parse(source, filename="test.m")
        label = routine.labels[0]
        assert label.body.statements[0].comment == "my comment"

    def test_label_line_no_comment(self, parser):
        """No comment → stmt.comment is None."""
        source = "TEST SET X=1\n"
        routine = parser.parse(source, filename="test.m")
        label = routine.labels[0]
        assert label.body.statements[0].comment is None

    def test_continuation_line_with_comment(self, parser):
        """Comment on continuation line is attached to first statement."""
        source = "TEST\n SET X=1 ; continuation comment\n"
        routine = parser.parse(source, filename="test.m")
        label = routine.labels[0]
        assert label.body.statements[0].comment == "continuation comment"

    def test_continuation_line_no_comment(self, parser):
        """Continuation line without comment → stmt.comment is None."""
        source = "TEST\n SET X=1\n"
        routine = parser.parse(source, filename="test.m")
        label = routine.labels[0]
        assert label.body.statements[0].comment is None

    def test_semicolon_in_string_not_comment(self, parser):
        """Semicolons inside string literals must not be treated as comments."""
        source = 'TEST WRITE "hello;world"\n'
        routine = parser.parse(source, filename="test.m")
        label = routine.labels[0]
        assert label.body.statements[0].comment is None

    def test_string_with_semicolons_and_trailing_comment(self, parser):
        """String semicolons ignored, trailing comment extracted."""
        source = 'TEST WRITE "a;b" ; real\n'
        routine = parser.parse(source, filename="test.m")
        label = routine.labels[0]
        assert label.body.statements[0].comment == "real"

    def test_multiple_statements_comment_on_first(self, parser):
        """When multiple commands on one line, comment goes on first statement."""
        source = "TEST SET X=1 WRITE X ; end of line\n"
        routine = parser.parse(source, filename="test.m")
        label = routine.labels[0]
        stmts = label.body.statements
        assert stmts[0].comment == "end of line"
        # Second statement should NOT have the comment
        if len(stmts) > 1:
            assert stmts[1].comment is None

    def test_dotted_continuation_with_comment(self, parser):
        """Dotted block line with comment."""
        source = "TEST\n . SET X=1 ; dotted comment\n"
        routine = parser.parse(source, filename="test.m")
        label = routine.labels[0]
        # The DO expansion should carry the comment through structuring
        stmts = label.body.statements
        # Find the SET statement (may be nested in DO body)
        found_comment = False
        for stmt in stmts:
            if hasattr(stmt, "comment") and stmt.comment == "dotted comment":
                found_comment = True
                break
        assert found_comment
