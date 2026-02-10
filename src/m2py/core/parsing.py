"""String-level parsing utilities for MUMPS name/subscript expressions.

This module provides the single source of truth for parsing subscripted
MUMPS variable names (e.g. ``ARR(1,"A,B",3)``) and canonicalizing
raw subscript strings to their Python storage types.

Replaces three independent ``_parse_subscripted_name`` implementations
in runtime/__init__.py, core/scope.py, and core/indirection.py.

Constitution III: Strict layer separation — core/ has no codegen imports.
"""

from __future__ import annotations

from typing import Union

from m2py.core.tokenizer import split_at_toplevel


def parse_subscripted_name(name: str) -> tuple[str, list[str]]:
    """Parse a possibly-subscripted MUMPS name.

    Args:
        name: e.g. ``'ARR(1,"A,B",3)'`` or ``'X'``

    Returns:
        ``(base_name, subscript_list)`` where subscript_list is ``[]``
        for unsubscripted names. Subscripts are raw strings — no
        numeric conversion or quote stripping.

    Examples:
        >>> parse_subscripted_name('ARR(1,2)')
        ('ARR', ['1', '2'])
        >>> parse_subscripted_name('X')
        ('X', [])
        >>> parse_subscripted_name('A("B,C")')
        ('A', ['"B,C"'])
        >>> parse_subscripted_name('^GLO(1)')
        ('^GLO', ['1'])
    """
    paren_pos = name.find("(")
    if paren_pos == -1:
        return (name, [])

    base_name = name[:paren_pos]

    # Must end with closing paren
    if not name.endswith(")"):
        return (name, [])

    subs_str = name[paren_pos + 1 : -1]
    if not subs_str:
        return (base_name, [])

    subscripts = split_at_toplevel(subs_str, delimiter=",", respect_quotes=True)
    return (base_name, subscripts)


def canonicalize_subscript(sub: str) -> Union[int, float, str]:
    """Convert a raw subscript string to its canonical Python type.

    Numeric strings → int or float.  Non-numeric → str.
    Used only by runtime storage operations where type matters
    for lookup matching.

    Args:
        sub: Raw subscript string (may include quotes)

    Returns:
        ``int`` if the string is a valid integer,
        ``float`` if it contains a decimal point and is valid,
        otherwise the original ``str``.

    Examples:
        >>> canonicalize_subscript('1')
        1
        >>> canonicalize_subscript('3.14')
        3.14
        >>> canonicalize_subscript('hello')
        'hello'
        >>> canonicalize_subscript('"key"')
        '"key"'
    """
    try:
        if "." in sub:
            return float(sub)
        return int(sub)
    except ValueError:
        return sub
