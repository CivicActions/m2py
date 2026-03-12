"""Indent-aware code emitter for Python code generation.

Provides a builder pattern for generating properly indented Python code
without string concatenation or template engines.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator


class CodeEmitter:
    """Builder for indent-aware Python code generation.

    Maintains indentation state and builds code line-by-line.
    Preferred over string concatenation for cleaner code generation.

    Example:
        >>> emitter = CodeEmitter()
        >>> emitter.line("def foo():")
        >>> with emitter.indented():
        ...     emitter.line("return 42")
        >>> print(emitter.get_code())
        def foo():
            return 42
    """

    def __init__(self, indent: str = "    ") -> None:
        """Initialize emitter with indent string.

        Args:
            indent: String to use for each indent level (default: 4 spaces)
        """
        self._indent = indent
        self._level = 0
        self._lines: list[str] = []
        self._deferred_functions: list[str] = []

    def line(self, code: str) -> None:
        """Emit a line of code at current indent level.

        Args:
            code: Code line (without trailing newline)
        """
        prefix = self._indent * self._level
        self._lines.append(f"{prefix}{code}")

    def blank(self) -> None:
        """Emit a blank line (no indentation)."""
        self._lines.append("")

    def indent(self) -> None:
        """Increase indent level by one.

        Use this with dedent() for non-context-manager indentation control.
        Prefer indented() context manager when possible.
        """
        self._level += 1

    def dedent(self) -> None:
        """Decrease indent level by one.

        Use this with indent() for non-context-manager indentation control.
        Prefer indented() context manager when possible.
        """
        self._level -= 1

    @contextmanager
    def indented(self) -> Iterator[None]:
        """Context manager that increases indent level.

        Usage:
            >>> with emitter.indented():
            ...     emitter.line("indented code")
        """
        self._level += 1
        try:
            yield
        finally:
            self._level -= 1

    def append(self, text: str) -> None:
        """Append text to the last emitted line.

        Useful for building up complex expressions.

        Args:
            text: Text to append (no newline added)

        Raises:
            IndexError: If no lines have been emitted yet
        """
        self._lines[-1] += text

    def emit_deferred_functions(self) -> None:
        """Emit all deferred function definitions at module level.

        Call this at indent level 0, before the ``if __name__`` block,
        so that helper functions are defined before they may be called.
        """
        for func_code in self._deferred_functions:
            self._lines.append("")
            self._lines.extend(func_code.rstrip("\n").split("\n"))
        self._deferred_functions.clear()

    def get_code(self) -> str:
        """Get the complete generated code.

        Returns:
            All emitted lines joined with newlines, trailing newline included
        """
        return "\n".join(self._lines) + "\n"


__all__ = ["CodeEmitter"]
