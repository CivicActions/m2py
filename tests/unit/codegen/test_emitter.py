"""Tests for CodeEmitter."""

import pytest

from m2py.codegen.emitter import CodeEmitter


pytestmark = pytest.mark.codegen


class TestCodeEmitter:
    """Tests for the CodeEmitter class."""

    def test_basic_line(self):
        """Emit a basic line of code."""
        emitter = CodeEmitter()
        emitter.line("x = 1")
        assert emitter.get_code() == "x = 1\n"

    def test_multiple_lines(self):
        """Emit multiple lines."""
        emitter = CodeEmitter()
        emitter.line("x = 1")
        emitter.line("y = 2")
        assert emitter.get_code() == "x = 1\ny = 2\n"

    def test_indented_context(self):
        """Use indented() context manager."""
        emitter = CodeEmitter()
        emitter.line("def foo():")
        with emitter.indented():
            emitter.line("return 42")
        assert emitter.get_code() == "def foo():\n    return 42\n"

    def test_manual_indent_dedent(self):
        """Use manual indent() and dedent()."""
        emitter = CodeEmitter()
        emitter.line("if True:")
        emitter.indent()
        emitter.line("pass")
        emitter.dedent()
        emitter.line("else:")
        assert emitter.get_code() == "if True:\n    pass\nelse:\n"

    def test_blank_line(self):
        """Emit blank lines."""
        emitter = CodeEmitter()
        emitter.line("x = 1")
        emitter.blank()
        emitter.line("y = 2")
        assert emitter.get_code() == "x = 1\n\ny = 2\n"

    def test_append_to_line(self):
        """Append text to existing line."""
        emitter = CodeEmitter()
        emitter.line("x = ")
        emitter.append("1")
        assert emitter.get_code() == "x = 1\n"

    def test_append_to_empty(self):
        """Append when no lines exist creates new line."""
        emitter = CodeEmitter()
        emitter.append("test")
        assert emitter.get_code() == "test\n"

    def test_get_lines(self):
        """Get list of lines."""
        emitter = CodeEmitter()
        emitter.line("a")
        emitter.line("b")
        assert emitter.get_lines() == ["a", "b"]

    def test_current_indent(self):
        """Check current indent level."""
        emitter = CodeEmitter()
        assert emitter.current_indent == 0
        emitter.indent()
        assert emitter.current_indent == 1
        emitter.indent()
        assert emitter.current_indent == 2
        emitter.dedent()
        assert emitter.current_indent == 1

    def test_empty_code(self):
        """Empty emitter returns empty string."""
        emitter = CodeEmitter()
        assert emitter.get_code() == ""

    def test_custom_indent(self):
        """Use custom indent string."""
        emitter = CodeEmitter(indent="\t")
        emitter.line("x = 1")
        with emitter.indented():
            emitter.line("y = 2")
        assert emitter.get_code() == "x = 1\n\ty = 2\n"

    def test_nested_indent(self):
        """Nested indentation."""
        emitter = CodeEmitter()
        emitter.line("level 0")
        with emitter.indented():
            emitter.line("level 1")
            with emitter.indented():
                emitter.line("level 2")
            emitter.line("back to 1")
        emitter.line("back to 0")
        expected = "level 0\n    level 1\n        level 2\n    back to 1\nback to 0\n"
        assert emitter.get_code() == expected
