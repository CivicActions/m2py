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

    def test_initial_lines_empty(self):
        """Initial lines list is empty."""
        emitter = CodeEmitter()
        assert emitter._lines == []


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
        assert emitter._lines == ["x = 1"]

    def test_emits_multiple_lines(self):
        """Emits multiple lines of code."""
        emitter = CodeEmitter()
        emitter.line("x = 1")
        emitter.line("y = 2")
        assert emitter._lines == ["x = 1", "y = 2"]

    def test_applies_current_indent(self):
        """Applies current indent level to emitted lines."""
        emitter = CodeEmitter()
        emitter.indent()
        emitter.line("indented code")
        assert emitter._lines == ["    indented code"]


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
        assert emitter._lines == ["code", "", "more code"]


# =============================================================================
# Tests for indent() and dedent() Methods
# =============================================================================


@pytest.mark.codegen
class TestCodeEmitterIndentDedent:
    """Tests for CodeEmitter.indent() and dedent()."""

    def test_indent_increases_level(self):
        """indent() increases indent level by one."""
        emitter = CodeEmitter()
        assert emitter._level == 0
        emitter.indent()
        assert emitter._level == 1

    def test_dedent_decreases_level(self):
        """dedent() decreases indent level by one."""
        emitter = CodeEmitter()
        emitter.indent()
        emitter.indent()
        assert emitter._level == 2
        emitter.dedent()
        assert emitter._level == 1

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
        assert emitter._lines == [
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
        assert emitter._lines == [
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
        assert emitter._lines == [
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
        assert emitter._level == 0
        emitter.line("back to normal")
        assert emitter._lines[-1] == "back to normal"


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
        assert emitter._lines == ["x = 1 + 2"]


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

    def test_empty_emitter_returns_newline(self):
        """Empty emitter returns a newline."""
        emitter = CodeEmitter()
        assert emitter.get_code() == "\n"

    def test_includes_trailing_newline(self):
        """Includes trailing newline."""
        emitter = CodeEmitter()
        emitter.line("x = 1")
        assert emitter.get_code().endswith("\n")


# =============================================================================
# Tests for Deferred Functions
# =============================================================================


@pytest.mark.codegen
class TestCodeEmitterDeferredFunctions:
    """Tests for emit_deferred_functions() support."""

    def test_deferred_functions_initially_empty(self):
        """Deferred functions list starts empty."""
        emitter = CodeEmitter()
        assert emitter._deferred_functions == []

    def test_emit_deferred_appends_to_output(self):
        """emit_deferred_functions() appends deferred code to output lines."""
        emitter = CodeEmitter()
        emitter.line("import foo")
        emitter._deferred_functions.append("def helper():\n    pass")
        emitter.emit_deferred_functions()
        code = emitter.get_code()
        assert "def helper():" in code
        assert "    pass" in code
        assert code.index("import foo") < code.index("def helper():")

    def test_emit_deferred_clears_list(self):
        """After emit, the deferred list is cleared."""
        emitter = CodeEmitter()
        emitter._deferred_functions.append("def f(): pass")
        emitter.emit_deferred_functions()
        assert emitter._deferred_functions == []

    def test_emit_deferred_multiple_functions(self):
        """Multiple deferred functions are all emitted in order."""
        emitter = CodeEmitter()
        emitter._deferred_functions.append("def first():\n    return 1")
        emitter._deferred_functions.append("def second():\n    return 2")
        emitter.emit_deferred_functions()
        code = emitter.get_code()
        assert code.index("def first():") < code.index("def second():")

    def test_emit_deferred_noop_when_empty(self):
        """Calling emit_deferred_functions with no deferred code is a no-op."""
        emitter = CodeEmitter()
        emitter.line("x = 1")
        emitter.emit_deferred_functions()
        assert emitter.get_code() == "x = 1\n"

    def test_deferred_functions_separated_by_blank_line(self):
        """Each deferred function is preceded by a blank line."""
        emitter = CodeEmitter()
        emitter.line("# main code")
        emitter._deferred_functions.append("def helper():\n    pass")
        emitter.emit_deferred_functions()
        lines = emitter._lines
        helper_idx = next(i for i, l in enumerate(lines) if "def helper" in l)
        assert lines[helper_idx - 1] == ""
