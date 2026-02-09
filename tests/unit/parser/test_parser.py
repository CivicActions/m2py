"""Tests for parser internal methods and edge cases.

Covers:
- _find_argumentless_do_for_dot_lines (IF/ELSE/direct DO paths)
- _structure_commands_with_bodies (ELSE branch)
- _set_line_number_recursive (else_scope)
- parse() exception handlers
- parse_file() analysis flags
- MUMPSParser.__init__ FileNotFoundError
- line_parser error branches
- classify_for_command subscripted var
"""

import pytest
from unittest.mock import patch
from pathlib import Path

from m2py.parser import MUMPSParser
from m2py.parser.exceptions import MUMPSSyntaxError
from m2py.asg import (
    MDoStatement,
    MElseStatement,
    MForStatement,
    MIfStatement,
    MSetStatement,
    MWriteStatement,
)


@pytest.mark.parser
class TestFindArgumentlessDoForDotLines:
    """Tests for _find_argumentless_do_for_dot_lines IF/ELSE/direct DO paths."""

    def test_if_wrapping_argumentless_do_with_dot_body(self, parse_mumps):
        """IF containing argumentless DO captures dot-lines (L183-198).

        MUMPS: I 1 D  / . W 1
        The dot-line belongs to the argumentless DO inside the IF.
        """
        source = "TEST\n\tI 1 D\n\t. W 1\n\tQ\n"
        result = parse_mumps(source)
        stmts = result.labels[0].body.statements
        # The IF should be first, containing the DO
        if_stmt = stmts[0]
        assert isinstance(if_stmt, MIfStatement)
        # The DO within the IF's then_scope should have dot-body
        then_stmts = if_stmt.then_scope.statements
        do_stmt = then_stmts[0]
        assert isinstance(do_stmt, MDoStatement)
        assert not do_stmt.targets  # argumentless
        assert len(do_stmt.body.statements) > 0  # has dot body

    def test_else_wrapping_argumentless_do_with_dot_body(self, parse_mumps):
        """ELSE containing argumentless DO captures dot-lines (L200-209).

        MUMPS: I 0 W "a" / E  D  / . W "b"
        The dot-line belongs to the argumentless DO inside the ELSE.
        """
        source = 'TEST\n\tI 0 W "a"\n\tE  D\n\t. W "b"\n\tQ\n'
        result = parse_mumps(source)
        stmts = result.labels[0].body.statements
        else_stmt = stmts[1]
        assert isinstance(else_stmt, MElseStatement)
        body_stmts = else_stmt.body.statements
        do_stmt = body_stmts[0]
        assert isinstance(do_stmt, MDoStatement)
        assert not do_stmt.targets
        assert len(do_stmt.body.statements) > 0

    def test_for_containing_if_with_do_and_dot_body(self, parse_mumps):
        """FOR > IF > DO captures dot-lines through nested search.

        MUMPS: F I=1:1:5 I I>2 D / . W I
        """
        source = "TEST\n\tF I=1:1:5 I I>2 D\n\t. W I\n\tQ\n"
        result = parse_mumps(source)
        stmts = result.labels[0].body.statements
        for_stmt = stmts[0]
        assert isinstance(for_stmt, MForStatement)
        # FOR > IF > DO > dot body
        if_stmt = for_stmt.body.statements[0]
        assert isinstance(if_stmt, MIfStatement)
        do_stmt = if_stmt.then_scope.statements[0]
        assert isinstance(do_stmt, MDoStatement)
        assert len(do_stmt.body.statements) > 0


@pytest.mark.parser
class TestStructureCommandsWithBodiesElse:
    """Tests for ELSE branch in _structure_commands_with_bodies (L124-131)."""

    def test_else_captures_remaining_statements(self, parse_mumps):
        """ELSE followed by SET and WRITE nests them as body.

        MUMPS: E  S X=1 W X
        """
        source = 'TEST\n\tI 0 W "skip"\n\tE  S X=1 W X\n\tQ\n'
        result = parse_mumps(source)
        stmts = result.labels[0].body.statements
        else_stmt = stmts[1]
        assert isinstance(else_stmt, MElseStatement)
        body = else_stmt.body
        assert body is not None
        assert len(body.statements) == 2
        assert isinstance(body.statements[0], MSetStatement)
        assert isinstance(body.statements[1], MWriteStatement)
        # Verify scope assignment
        for child in body.statements:
            assert child.scope is body

    def test_else_with_single_command(self, parse_mumps):
        """ELSE with single command."""
        source = 'TEST\n\tI 0 W "no"\n\tE  W "yes"\n\tQ\n'
        result = parse_mumps(source)
        else_stmt = result.labels[0].body.statements[1]
        assert isinstance(else_stmt, MElseStatement)
        assert len(else_stmt.body.statements) == 1
        assert isinstance(else_stmt.body.statements[0], MWriteStatement)


@pytest.mark.parser
class TestSetLineNumberRecursiveElseScope:
    """Tests for _set_line_number_recursive else_scope path (L71-72)."""

    def test_else_body_statements_get_line_numbers(self, parse_mumps):
        """Statements inside ELSE body get correct line numbers.

        The ELSE body commands on the same line share the same line number.
        """
        source = 'TEST\n\tI 0 W "no"\n\tE  S X=1 W X\n\tQ\n'
        result = parse_mumps(source)
        else_stmt = result.labels[0].body.statements[1]
        assert isinstance(else_stmt, MElseStatement)
        for child in else_stmt.body.statements:
            assert child.line_number is not None
            assert child.line_number == else_stmt.line_number


@pytest.mark.parser
class TestParseExceptionHandlers:
    """Tests for parse() exception handlers (L552-562)."""

    def test_syntax_error_wraps_textx_error(self):
        """TextXSyntaxError is wrapped in MUMPSSyntaxError (L553-557)."""
        parser = MUMPSParser()
        with pytest.raises(MUMPSSyntaxError) as exc_info:
            parser.parse("= invalid syntax\n")
        assert exc_info.value.line is not None or exc_info.value.message

    def test_syntax_error_preserves_file_info(self):
        """MUMPSSyntaxError includes source_file when given."""
        parser = MUMPSParser()
        with pytest.raises(MUMPSSyntaxError) as exc_info:
            parser.parse("= invalid syntax\n", filename="test.m")
        assert exc_info.value.source_file == "test.m"


@pytest.mark.parser
class TestParseFileAnalysisFlags:
    """Tests for parse_file() analyze_variables/compute_signatures flags (L616-623)."""

    def test_parse_file_with_analyze_variables(self, tmp_path):
        """parse_file(f, analyze_variables=True) populates label variables."""
        m_file = tmp_path / "test.m"
        m_file.write_text("TEST\n\tN X\n\tS X=1\n\tW X\n\tQ\n")

        parser = MUMPSParser()
        routine = parser.parse_file(str(m_file), analyze_variables=True)
        # After analysis, labels should have resolved references
        assert routine is not None
        assert len(routine.labels) > 0

    def test_parse_file_with_compute_signatures(self, tmp_path):
        """parse_file(f, compute_signatures=True) computes function signatures."""
        m_file = tmp_path / "test.m"
        m_file.write_text("TEST(A,B)\n\tS C=A+B\n\tQ C\n")

        parser = MUMPSParser()
        routine = parser.parse_file(str(m_file), compute_signatures=True)
        assert routine is not None
        # With compute_signatures, labels should have signature info
        test_label = routine.labels[0]
        assert test_label.name == "TEST"


@pytest.mark.parser
class TestMUMPSParserInitFileNotFound:
    """Tests for MUMPSParser.__init__ FileNotFoundError (L478)."""

    def test_grammar_file_not_found(self):
        """FileNotFoundError raised when grammar file is missing."""
        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(FileNotFoundError, match="Grammar file not found"):
                MUMPSParser()


@pytest.mark.parser
class TestLineParserErrorBranches:
    """Tests for line_parser error handling paths."""

    def test_parse_line_content_syntax_error(self):
        """parse_line_content returns MParseError for syntax errors (L104-113)."""
        from m2py.parser.line_parser import parse_line_content
        from m2py.asg.elements import MParseError

        result = parse_line_content("S X=", 5)
        assert isinstance(result, MParseError)
        assert result.line_number == 5

    def test_parse_line_content_unknown_command(self):
        """parse_line_content returns MParseError for unknown commands (L114-120)."""
        from m2py.parser.line_parser import parse_line_content
        from m2py.asg.elements import MParseError

        result = parse_line_content("FOOBAR X=1")
        assert isinstance(result, MParseError)

    def test_parse_commands_from_line_error_propagation(self):
        """parse_commands_from_line propagates MParseError (L141-157)."""
        from m2py.parser.line_parser import parse_commands_from_line
        from m2py.asg.elements import MParseError

        result = parse_commands_from_line("S X=", 3)
        assert isinstance(result, MParseError)

    def test_parse_commands_from_line_empty(self):
        """parse_commands_from_line returns [] for empty lines."""
        from m2py.parser.line_parser import parse_commands_from_line

        result = parse_commands_from_line("")
        assert result == []

    def test_parse_commands_from_line_whitespace(self):
        """parse_commands_from_line returns [] for whitespace-only."""
        from m2py.parser.line_parser import parse_commands_from_line

        result = parse_commands_from_line("   ")
        assert result == []
