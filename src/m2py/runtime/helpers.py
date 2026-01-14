"""Runtime helper functions for MUMPS special operations.

Spec 009: Provides helper functions for operations that cannot be expressed
as simple Python expressions:

- m_set_piece: LHS $PIECE assignment (S $P(X,"^",2)="NEW")
- m_set_extract: LHS $EXTRACT assignment (S $E(X,2,3)="XX")
- m_data: $DATA function for local arrays
- m_data_global: $DATA function for global variables

These helpers are imported in generated code and called at runtime.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from m2py.runtime import MArray
    from m2py.runtime.globals import GlobalStorageBackend


def m_set_piece(
    var_getter: Callable[[], str],
    var_setter: Callable[[str], None],
    delimiter: str,
    piece_from: int,
    piece_to: int | None,
    value: str,
) -> None:
    """Set piece(s) of a string variable (LHS $PIECE).

    Equivalent to: SET $PIECE(var, delimiter, piece_from, piece_to) = value

    Args:
        var_getter: Callable returning current variable value
        var_setter: Callable to set new variable value
        delimiter: Piece delimiter string
        piece_from: Starting piece number (1-indexed)
        piece_to: Ending piece number (1-indexed), or None for single piece
        value: Replacement value

    Behavior:
        - If piece_from > current piece count, pads with empty pieces
        - If piece_to specified, replaces range [piece_from, piece_to]
        - delimiter="" uses each character as delimiter (implementation-specific)

    Examples:
        # S X="A^B^C" S $P(X,"^",2)="NEW" → X="A^NEW^C"
        m_set_piece(lambda: "A^B^C", setter, "^", 2, None, "NEW")

        # S X="" S $P(X,"^",3)="X" → X="^^X"
        m_set_piece(lambda: "", setter, "^", 3, None, "X")
    """
    # Get current value (empty string if undefined/None)
    current = var_getter() or ""

    # Normalize piece_to: if None, single piece replacement
    if piece_to is None:
        piece_to = piece_from

    # Split by delimiter (preserving all parts)
    if delimiter:
        parts = current.split(delimiter)
    else:
        # Empty delimiter edge case - treat each character as a delimiter
        parts = list(current) if current else [""]

    # Convert to 0-indexed
    from_idx = piece_from - 1
    to_idx = piece_to - 1

    # Pad with empty strings if needed to reach the target piece(s)
    while len(parts) <= to_idx:
        parts.append("")

    # Replace the range [from_idx, to_idx] with the value
    # Note: range is inclusive in MUMPS semantics
    new_parts = parts[:from_idx] + [value] + parts[to_idx + 1 :]

    # Join and set the result
    result = delimiter.join(new_parts)
    var_setter(result)


def m_set_extract(
    var_getter: Callable[[], str],
    var_setter: Callable[[str], None],
    from_pos: int,
    to_pos: int | None,
    value: str,
) -> None:
    """Set character(s) of a string variable (LHS $EXTRACT).

    Equivalent to: SET $EXTRACT(var, from_pos, to_pos) = value

    Args:
        var_getter: Callable returning current variable value
        var_setter: Callable to set new variable value
        from_pos: Starting position (1-indexed)
        to_pos: Ending position (1-indexed), or None (defaults to from_pos)
        value: Replacement string

    Behavior:
        - Positions are 1-indexed and inclusive
        - If from_pos > string length, pads with spaces
        - Replacement can be shorter or longer than original range

    Examples:
        # S X="HELLO" S $E(X,2,3)="XX" → X="HXXLO"
        m_set_extract(lambda: "HELLO", setter, 2, 3, "XX")

        # S X="AB" S $E(X,5)="X" → X="AB  X"
        m_set_extract(lambda: "AB", setter, 5, None, "X")
    """
    # Get current value (empty string if undefined/None)
    current = var_getter() or ""

    # Normalize to_pos: if None, single position
    if to_pos is None:
        to_pos = from_pos

    # Convert to 0-indexed
    from_idx = from_pos - 1
    to_idx = to_pos - 1

    # Pad with spaces if needed to reach the start position
    if from_idx > len(current):
        current = current + " " * (from_idx - len(current))

    # Build the result: before + value + after
    # "before" is everything up to from_idx
    # "after" is everything after to_idx (inclusive, so to_idx+1)
    before = current[:from_idx]
    after = current[to_idx + 1 :] if to_idx + 1 < len(current) else ""

    result = before + value + after
    var_setter(result)


def m_data(array: MArray | None, subscripts: tuple[str, ...] = ()) -> int:
    """Return $DATA value for local array variable.

    Args:
        array: MArray instance or None (undefined variable)
        subscripts: Tuple of subscript values to navigate into array

    Returns:
        0 - Undefined, no descendants
        1 - Defined, no descendants
        10 - Undefined, has descendants
        11 - Defined AND has descendants

    Examples:
        m_data(None) → 0  # undefined variable
        m_data(MArray(value="1")) → 1  # value only
        m_data(arr_with_children_only) → 10  # children only
        m_data(arr_with_both) → 11  # value AND children
    """
    if array is None:
        return 0
    # Navigate to target node via subscripts
    node = array
    for sub in subscripts:
        # MArray may use string or numeric keys depending on how SET was generated
        # Try the subscript as-is first, then try numeric conversion
        key = sub
        if key not in node._children:
            # Try converting string to int for numeric subscripts
            try:
                key = int(sub)
            except (ValueError, TypeError):
                pass
        if key not in node._children:
            return 0
        node = node._children[key]
    return node.data()


def m_data_global(
    backend: GlobalStorageBackend,
    name: str,
    subscripts: tuple[str, ...],
) -> int:
    """Return $DATA value for global variable.

    Args:
        backend: GlobalStorageBackend instance
        name: Global name without caret (e.g., "PATIENT")
        subscripts: Tuple of subscript values

    Returns:
        0 - Undefined, no descendants
        1 - Defined, no descendants
        10 - Undefined, has descendants
        11 - Defined AND has descendants

    Note:
        Delegates to backend.data() which updates naked indicator.
    """
    return backend.data(name, subscripts)
