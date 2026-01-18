"""Unit tests for CodeEmitter (emitter.py).

Tests for the indent-aware Python code generation builder.
"""

import pytest

from m2py.codegen.emitter import CodeEmitter


# =============================================================================
# Tests for CodeEmitter Initialization
# =============================================================================


@pytest.mark.codegen
class TestCodeEmitterInit:
    """Tests for CodeEmitter.__init__()."""

    def test_default_indent(self):
        """Default indent is 4 spaces."""
        emitter = CodeEmitter()
        assert emitter._indent == "    "

    def test_custom_indent(self):
        """Can use custom indent string."""
        emitter = CodeEmitter(indent="\t")
        assert emitter._indent == "\t"

    def test_initial_level_is_zero(self):
        """Initial indent level is 0."""
        emitter = CodeEmitter()
        assert emitter._level == 0
        assert emitter.current_indent == 0

    def test_initial_lines_empty(self):
        """Initial lines list is empty."""
        emitter = CodeEmitter()
        assert emitter.get_lines() == []


# =============================================================================
# Tests for line() Method
# =============================================================================


@pytest.mark.codegen
class TestCodeEmitterLine:
    """Tests for CodeEmitter.line()."""

    def test_emits_single_line(self):
        """Emits a single line of code."""
        emitter = CodeEmitter()
        emitter.line("x = 1")
        assert emitter.get_lines() == ["x = 1"]

    def test_emits_multiple_lines(self):
        """Emits multiple lines of code."""
        emitter = CodeEmitter()
        emitter.line("x = 1")
        emitter.line("y = 2")
        assert emitter.get_lines() == ["x = 1", "y = 2"]

    def test_applies_current_indent(self):
        """Applies current indent level to emitted lines."""
        emitter = CodeEmitter()
        emitter.indent()
        emitter.line("indented code")
        assert emitter.get_lines() == ["    indented code"]


# =============================================================================
# Tests for blank() Method
# =============================================================================


@pytest.mark.codegen
class TestCodeEmitterBlank:
    """Tests for CodeEmitter.blank()."""

    def test_emits_blank_line(self):
        """Emits a blank line."""
        emitter = CodeEmitter()
        emitter.line("code")
        emitter.blank()
        emitter.line("more code")
        assert emitter.get_lines() == ["code", "", "more code"]


# =============================================================================
# Tests for indent() and dedent() Methods
# =============================================================================


@pytest.mark.codegen
class TestCodeEmitterIndentDedent:
    """Tests for CodeEmitter.indent() and dedent()."""

    def test_indent_increases_level(self):
        """indent() increases indent level by one."""
        emitter = CodeEmitter()
        assert emitter.current_indent == 0
        emitter.indent()
        assert emitter.current_indent == 1

    def test_dedent_decreases_level(self):
        """dedent() decreases indent level by one."""
        emitter = CodeEmitter()
        emitter.indent()
        emitter.indent()
        assert emitter.current_indent == 2
        emitter.dedent()
        assert emitter.current_indent == 1

    def test_indent_dedent_affects_lines(self):
        """indent/dedent affect subsequent lines."""
        emitter = CodeEmitter()
        emitter.line("level 0")
        emitter.indent()
        emitter.line("level 1")
        emitter.indent()
        emitter.line("level 2")
        emitter.dedent()
        emitter.line("back to level 1")
        emitter.dedent()
        emitter.line("back to level 0")
        assert emitter.get_lines() == [
            "level 0",
            "    level 1",
            "        level 2",
            "    back to level 1",
            "back to level 0",
        ]


# =============================================================================
# Tests for indented() Context Manager
# =============================================================================


@pytest.mark.codegen
class TestCodeEmitterIndentedContext:
    """Tests for CodeEmitter.indented() context manager."""

    def test_context_manager_increases_indent(self):
        """Context manager increases indent inside block."""
        emitter = CodeEmitter()
        emitter.line("def foo():")
        with emitter.indented():
            emitter.line("return 42")
        emitter.line("# outside")
        assert emitter.get_lines() == [
            "def foo():",
            "    return 42",
            "# outside",
        ]

    def test_nested_context_managers(self):
        """Nested context managers stack indent levels."""
        emitter = CodeEmitter()
        emitter.line("class Foo:")
        with emitter.indented():
            emitter.line("def bar(self):")
            with emitter.indented():
                emitter.line("pass")
        assert emitter.get_lines() == [
            "class Foo:",
            "    def bar(self):",
            "        pass",
        ]

    def test_context_restores_on_exception(self):
        """Context manager restores indent level even if exception raised."""
        emitter = CodeEmitter()
        try:
            with emitter.indented():
                emitter.line("some code")
                raise ValueError("test error")
        except ValueError:
            pass
        # Indent level should be restored
        assert emitter.current_indent == 0
        emitter.line("back to normal")
        assert emitter.get_lines()[-1] == "back to normal"


# =============================================================================
# Tests for append() Method
# =============================================================================


@pytest.mark.codegen
class TestCodeEmitterAppend:
    """Tests for CodeEmitter.append()."""

    def test_append_to_last_line(self):
        """Appends text to the last emitted line."""
        emitter = CodeEmitter()
        emitter.line("x = 1")
        emitter.append(" + 2")
        assert emitter.get_lines() == ["x = 1 + 2"]

    def test_append_creates_line_if_empty(self):
        """Append creates new line if no lines exist."""
        emitter = CodeEmitter()
        emitter.append("first content")
        assert emitter.get_lines() == ["first content"]

    def test_append_with_indent_when_empty(self):
        """Append applies indent when creating first line."""
        emitter = CodeEmitter()
        emitter.indent()
        emitter.append("indented content")
        assert emitter.get_lines() == ["    indented content"]


# =============================================================================
# Tests for get_code() Method
# =============================================================================


@pytest.mark.codegen
class TestCodeEmitterGetCode:
    """Tests for CodeEmitter.get_code()."""

    def test_returns_joined_lines(self):
        """Returns all lines joined with newlines."""
        emitter = CodeEmitter()
        emitter.line("line 1")
        emitter.line("line 2")
        assert emitter.get_code() == "line 1\nline 2\n"

    def test_empty_emitter_returns_empty_string(self):
        """Empty emitter returns empty string."""
        emitter = CodeEmitter()
        assert emitter.get_code() == ""

    def test_includes_trailing_newline(self):
        """Includes trailing newline."""
        emitter = CodeEmitter()
        emitter.line("x = 1")
        assert emitter.get_code().endswith("\n")


# =============================================================================
# Tests for get_lines() Method
# =============================================================================


@pytest.mark.codegen
class TestCodeEmitterGetLines:
    """Tests for CodeEmitter.get_lines()."""

    def test_returns_copy_of_lines(self):
        """Returns a copy of internal lines list."""
        emitter = CodeEmitter()
        emitter.line("test")
        lines = emitter.get_lines()
        lines.append("modified")
        # Original should be unchanged
        assert emitter.get_lines() == ["test"]


# =============================================================================
# Tests for current_indent Property
# =============================================================================


@pytest.mark.codegen
class TestCodeEmitterCurrentIndent:
    """Tests for CodeEmitter.current_indent property."""

    def test_reflects_indent_level(self):
        """Property reflects current indent level."""
        emitter = CodeEmitter()
        assert emitter.current_indent == 0
        emitter.indent()
        assert emitter.current_indent == 1
        emitter.indent()
        assert emitter.current_indent == 2
        emitter.dedent()
        assert emitter.current_indent == 1
