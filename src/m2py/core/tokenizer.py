"""Delimiter-aware string splitting respecting nesting and quotes.

This module provides the single source of truth for splitting strings
at top-level delimiters while respecting parenthesis nesting and
MUMPS double-quote semantics.

Replaces 13+ hand-rolled parenthesis-depth state machines scattered
across runtime/__init__.py, core/scope.py, and core/indirection.py.

Constitution III: Strict layer separation — core/ has no codegen imports.
"""

from __future__ import annotations


def split_at_toplevel(
    s: str,
    delimiter: str = ",",
    respect_quotes: bool = True,
) -> list[str]:
    """Split a string at top-level occurrences of delimiter.

    "Top-level" means not inside parentheses or (optionally) double quotes.
    Tracks parenthesis depth and optionally MUMPS-style double-quote state.

    Args:
        s: Input string
        delimiter: Character to split on (default: comma)
        respect_quotes: If True, don't split inside double quotes

    Returns:
        List of substrings. Empty input → [''].

    Examples:
        >>> split_at_toplevel('A,B,C')
        ['A', 'B', 'C']
        >>> split_at_toplevel('A(1,2),B')
        ['A(1,2)', 'B']
        >>> split_at_toplevel('A,"B,C",D')
        ['A', '"B,C"', 'D']
        >>> split_at_toplevel('')
        ['']
    """
    if not s:
        return [""]

    parts: list[str] = []
    current: list[str] = []
    depth = 0
    in_quotes = False
    i = 0

    while i < len(s):
        ch = s[i]

        if respect_quotes and ch == '"':
            if in_quotes:
                # Check for escaped quote ("")
                if i + 1 < len(s) and s[i + 1] == '"':
                    current.append('"')
                    current.append('"')
                    i += 2
                    continue
                else:
                    in_quotes = False
            else:
                in_quotes = True
            current.append(ch)
        elif not in_quotes:
            if ch == "(":
                depth += 1
                current.append(ch)
            elif ch == ")":
                depth -= 1
                current.append(ch)
            elif ch == delimiter and depth == 0:
                parts.append("".join(current))
                current = []
            else:
                current.append(ch)
        else:
            # Inside quotes — append everything
            current.append(ch)

        i += 1

    parts.append("".join(current))
    return parts
