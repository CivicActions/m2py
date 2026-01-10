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
        if not self._lines:
            # No lines yet - start a new line with proper indent
            prefix = self._indent * self._level
            self._lines.append(f"{prefix}{text}")
        else:
            self._lines[-1] += text

    def get_code(self) -> str:
        """Get the complete generated code.

        Returns:
            All emitted lines joined with newlines, trailing newline included
        """
        if not self._lines:
            return ""
        return "\n".join(self._lines) + "\n"

    def get_lines(self) -> list[str]:
        """Get list of all emitted lines.

        Returns:
            List of code lines (without newlines)
        """
        return list(self._lines)

    @property
    def current_indent(self) -> int:
        """Current indentation level (0-based).

        Returns:
            Number of indent levels currently active
        """
        return self._level


__all__ = ["CodeEmitter"]
