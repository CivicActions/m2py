"""Unit tests for compile_mumps_line() — the XECUTE pipeline entry-point.

Tests cover:
- Simple single-command strings
- Multi-command lines
- Control-flow structuring (FOR, IF, ELSE body nesting)
- Parse error propagation
- Empty / whitespace-only input
- QUIT context analysis inside FOR
"""

import pytest

from m2py.asg.elements import MParseError
from m2py.parser.compiler import compile_mumps_line


@pytest.mark.parser
class TestCompileMumpsLineBasic:
    """Basic compile_mumps_line scenarios."""

    def test_empty_string_returns_empty_list(self):
        result = compile_mumps_line("")
        assert result == []

    def test_whitespace_only_returns_empty_list(self):
        result = compile_mumps_line("   ")
        assert result == []

    def test_single_write_command(self):
        result = compile_mumps_line('W "Hello",!')
        assert not isinstance(result, MParseError)
        assert len(result) == 1
        assert result[0].__class__.__name__ == "MWriteStatement"

    def test_single_set_command(self):
        result = compile_mumps_line("S X=1")
        assert not isinstance(result, MParseError)
        assert len(result) == 1
        assert result[0].__class__.__name__ == "MSetStatement"

    def test_single_quit_command(self):
        result = compile_mumps_line("Q")
        assert not isinstance(result, MParseError)
        assert len(result) == 1
        assert result[0].__class__.__name__ == "MQuitStatement"


@pytest.mark.parser
class TestCompileMumpsLineMultiCommand:
    """Multi-command lines produce multiple statements."""

    def test_write_and_quit(self):
        result = compile_mumps_line("W 1,! Q")
        assert not isinstance(result, MParseError)
        assert len(result) == 2
        assert result[0].__class__.__name__ == "MWriteStatement"
        assert result[1].__class__.__name__ == "MQuitStatement"

    def test_set_write_quit(self):
        result = compile_mumps_line("S X=42 W X,! Q")
        assert not isinstance(result, MParseError)
        assert len(result) == 3
        class_names = [s.__class__.__name__ for s in result]
        assert class_names == ["MSetStatement", "MWriteStatement", "MQuitStatement"]


@pytest.mark.parser
class TestCompileMumpsLineControlFlow:
    """Control-flow structuring (FOR/IF/ELSE body nesting)."""

    def test_for_captures_remaining_as_body(self):
        result = compile_mumps_line("F I=1:1:3 W I,!")
        assert not isinstance(result, MParseError)
        # FOR consumes the WRITE as its body, so top-level has 1 statement
        assert len(result) == 1
        stmt = result[0]
        assert stmt.__class__.__name__ == "MForStatement"
        assert len(stmt.body.statements) >= 1
        assert stmt.body.statements[0].__class__.__name__ == "MWriteStatement"

    def test_if_captures_remaining_as_body(self):
        result = compile_mumps_line("I 1 W 1,!")
        assert not isinstance(result, MParseError)
        assert len(result) == 1
        stmt = result[0]
        assert stmt.__class__.__name__ == "MIfStatement"
        assert len(stmt.then_scope.statements) >= 1

    def test_nested_for_for(self):
        result = compile_mumps_line("F I=1:1:2 F J=1:1:2 W I*J,!")
        assert not isinstance(result, MParseError)
        assert len(result) == 1
        outer = result[0]
        assert outer.__class__.__name__ == "MForStatement"
        inner = outer.body.statements[0]
        assert inner.__class__.__name__ == "MForStatement"
        assert inner.body.statements[0].__class__.__name__ == "MWriteStatement"


@pytest.mark.parser
class TestCompileMumpsLineQuitContext:
    """QUIT context analysis ensures QUITs inside FOR generate break."""

    def test_quit_inside_for_marked_as_in_loop(self):
        result = compile_mumps_line("F I=1:1:10 Q:I>5")
        assert not isinstance(result, MParseError)
        assert len(result) == 1
        for_stmt = result[0]
        assert for_stmt.__class__.__name__ == "MForStatement"
        # The QUIT inside the FOR body should have exits_for set
        quit_stmt = for_stmt.body.statements[0]
        assert quit_stmt.__class__.__name__ == "MQuitStatement"
        # exits_for should point to the enclosing FOR statement
        assert hasattr(quit_stmt, "exits_for")
        assert quit_stmt.exits_for is for_stmt


@pytest.mark.parser
class TestCompileMumpsLineErrors:
    """Parse error handling."""

    def test_invalid_syntax_returns_parse_error(self):
        result = compile_mumps_line("@@INVALID@@SYNTAX@@")
        assert isinstance(result, MParseError)

    def test_parse_error_has_message(self):
        result = compile_mumps_line("@@BADPARSE@@")
        assert isinstance(result, MParseError)
        assert result.message  # non-empty error message
