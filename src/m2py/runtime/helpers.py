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
    raise NotImplementedError("m_set_piece: stub - implementation in Phase 3")


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
    raise NotImplementedError("m_set_extract: stub - implementation in Phase 4")


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
    raise NotImplementedError("m_data: stub - implementation in Phase 8")


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
    raise NotImplementedError("m_data_global: stub - implementation in Phase 8")
