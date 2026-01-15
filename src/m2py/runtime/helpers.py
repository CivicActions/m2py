"""Runtime helper functions for MUMPS special operations.

Spec 009: Provides helper functions for operations that cannot be expressed
as simple Python expressions:

- m_set_piece: LHS $PIECE assignment (S $P(X,"^",2)="NEW")
- m_set_extract: LHS $EXTRACT assignment (S $E(X,2,3)="XX")
- m_data: $DATA function for local arrays
- m_data_global: $DATA function for global variables

Spec 010: Extended with array traversal functions:
- m_order: $ORDER function for local arrays
- m_order_global: $ORDER function for global variables
- m_query: $QUERY function for local arrays
- m_query_global: $QUERY function for global variables

These helpers are imported in generated code and called at runtime.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Tuple

if TYPE_CHECKING:
    from m2py.runtime import MArray
    from m2py.runtime.globals import GlobalStorageBackend


def _mumps_collation_key(value: Any) -> Tuple[int, Any]:
    """Generate a sort key for MUMPS collation order.

    MUMPS collation order:
    1. Numeric values (sorted numerically, negatives first)
    2. String values (sorted by ASCII/UTF-8)

    The key returns a tuple (type_order, sort_value) where:
    - type_order: 0 for numeric, 1 for string
    - sort_value: the value to compare within the type

    Args:
        value: A subscript value (string, int, or float)

    Returns:
        Tuple for comparison in sorted()
    """
    # Check if value is numeric (can be int, float, or numeric string)
    if isinstance(value, (int, float)):
        return (0, float(value))

    # Try to parse string as a number
    if isinstance(value, str):
        try:
            # MUMPS considers numeric strings as numbers for collation
            num = float(value)
            return (0, num)
        except (ValueError, TypeError):
            # Not a numeric string, sort as string
            return (1, value)

    # Fallback for any other type
    return (1, str(value))


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

    Note:
        Per MUMPS spec, piece numbers <= 0 result in no modification.
    """
    # Per MUMPS spec: piece numbers <= 0 result in no modification
    if piece_from <= 0:
        return

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

    Note:
        Per YDB behavior, if from_pos > to_pos, no modification occurs.
    """
    # Get current value (empty string if undefined/None)
    current = var_getter() or ""

    # Normalize to_pos: if None, single position
    if to_pos is None:
        to_pos = from_pos

    # Per YDB behavior: if from_pos > to_pos, no modification occurs
    if from_pos > to_pos:
        return

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


def m_order(
    array: MArray | None,
    subscripts: tuple[str, ...],
    direction: int = 1,
) -> str:
    """Return next subscript in MUMPS collation order ($ORDER).

    Navigates to the parent level specified by all but the last subscript,
    then finds the next/previous subscript after the last subscript value.

    Args:
        array: MArray instance or None (undefined variable)
        subscripts: Tuple of subscript values. The last element is the
                   starting point for iteration. Use ("",) to get first/last.
        direction: 1 for forward (next), -1 for reverse (previous)

    Returns:
        Next/previous subscript as string, or "" if no more subscripts.

    MUMPS Collation Order:
        1. Negative numbers (most negative first)
        2. Zero
        3. Positive numbers (ascending)
        4. Strings (ASCII/UTF-8 order)

    Examples:
        # arr has children at 1, 2, 3
        m_order(arr, ("",), 1) → "1"   # First key forward
        m_order(arr, ("1",), 1) → "2"  # Next after 1
        m_order(arr, ("3",), 1) → ""   # No more keys forward
        m_order(arr, ("",), -1) → "3"  # First key reverse (i.e., last)
        m_order(arr, ("3",), -1) → "2" # Previous before 3

        # With parent subscripts: arr(1,1)=1, arr(1,2)=2
        m_order(arr, ("1", ""), 1) → "1"  # First child of arr(1)
        m_order(arr, ("1", "1"), 1) → "2" # Next after arr(1,1)
    """
    if array is None:
        return ""

    # Navigate to parent level (all but last subscript)
    # The last subscript is the starting point for the search
    if not subscripts:
        return ""

    parent_subs = subscripts[:-1]
    start_key = subscripts[-1]

    # Navigate to parent node
    node = array
    for sub in parent_subs:
        # Try to find the subscript (handle string/int key mismatches)
        key = sub
        if key not in node._children:
            try:
                key = int(sub)
            except (ValueError, TypeError):
                pass
        if key not in node._children:
            try:
                key = float(sub)
            except (ValueError, TypeError):
                pass
        if key not in node._children:
            return ""
        node = node._children[key]

    # Get all children keys sorted in MUMPS collation order
    keys = sorted(node._children.keys(), key=_mumps_collation_key)

    if direction == -1:
        keys = list(reversed(keys))

    if start_key == "":
        # Empty string means get first key in the current direction
        return str(keys[0]) if keys else ""

    # Find the next key after start_key
    # First, locate start_key in the sorted list
    start_sort_key = _mumps_collation_key(start_key)

    for key in keys:
        key_sort = _mumps_collation_key(key)
        if direction == 1:
            # Forward: find first key greater than start_key
            if key_sort > start_sort_key:
                return str(key)
        else:
            # Reverse: find first key less than start_key
            if key_sort < start_sort_key:
                return str(key)

    return ""


def m_order_global(
    backend: GlobalStorageBackend,
    name: str,
    subscripts: tuple[str, ...],
    direction: int = 1,
) -> str:
    """Return next subscript in MUMPS collation order for global variable.

    Args:
        backend: GlobalStorageBackend instance
        name: Global name without caret (e.g., "PATIENT")
        subscripts: Tuple of subscript values. Last element is starting point.
        direction: 1 for forward, -1 for reverse

    Returns:
        Next/previous subscript as string, or "" if no more subscripts.

    Note:
        Delegates to backend.order() which updates naked indicator.
    """
    return backend.order(name, subscripts, direction)


def _find_next_valued_node(
    node: "MArray",
    current_path: list[str],
    start_path: tuple[str, ...],
    at_start: bool,
) -> tuple[str, ...] | None:
    """Find the next valued node in depth-first traversal order.

    This is a helper function for m_query that performs the actual tree traversal.

    Args:
        node: Current MArray node to search from
        current_path: Path to this node (for building result)
        start_path: Starting point for search (find nodes after this)
        at_start: True if we should search from beginning of this subtree

    Returns:
        Tuple of subscripts to next valued node, or None if no more nodes
    """
    # Get children in collation order
    keys = sorted(node._children.keys(), key=_mumps_collation_key)

    for key in keys:
        str_key = str(key)
        child = node._children[key]
        child_path = current_path + [str_key]

        # Determine if we should explore this subtree
        if at_start:
            # We're searching from start - check all children
            should_explore = True
        elif len(start_path) == 0:
            # Start path exhausted, explore everything from here
            should_explore = True
        elif str_key == start_path[0]:
            # This key matches start path - recurse deeper
            result = _find_next_valued_node(
                child, child_path, start_path[1:], at_start=False
            )
            if result is not None:
                return result
            # Didn't find in this subtree, continue to siblings
            should_explore = False
        elif _mumps_collation_key(str_key) > _mumps_collation_key(start_path[0]):
            # This key is after start path at this level - explore fully
            should_explore = True
        else:
            # This key is before start path - skip
            should_explore = False

        if should_explore:
            # Check if this node has a value
            if child._value is not None:
                return tuple(child_path)

            # Recursively search children
            result = _find_next_valued_node(child, child_path, (), at_start=True)
            if result is not None:
                return result

    return None


def m_query(
    array: MArray | None,
    var_name: str,
    subscripts: tuple[str, ...],
) -> str:
    """Return full reference of next node in depth-first traversal ($QUERY).

    Args:
        array: MArray instance or None (undefined variable)
        var_name: Variable name for constructing reference string
        subscripts: Current position subscripts. Use ("",) to start from beginning.

    Returns:
        Full variable reference string (e.g., "A(1,2)"), or "" if no more nodes.

    MUMPS $QUERY semantics:
        - Returns the full reference of the next node that has a value
        - Traverses in depth-first order following MUMPS collation
        - Starting from empty string finds the first valued node
        - Returns empty string when no more valued nodes exist

    Examples:
        # arr(1,1)=1, arr(1,2)=2, arr(2,1)=3
        m_query(arr, "A", ("",)) → "A(1,1)"
        m_query(arr, "A", ("1", "1")) → "A(1,2)"
        m_query(arr, "A", ("1", "2")) → "A(2,1)"
        m_query(arr, "A", ("2", "1")) → ""
    """
    if array is None:
        return ""

    # Check if we're starting from empty string (find first valued node)
    if subscripts == ("",) or subscripts == ():
        # Start from beginning - find first valued node in entire tree
        result = _find_next_valued_node(array, [], (), at_start=True)
    else:
        # Find next valued node after the given subscripts
        result = _find_next_valued_node(array, [], subscripts, at_start=False)

    if result is None:
        return ""

    # Format as variable reference: "A(1,2,3)"
    if len(result) == 0:
        return var_name
    return f"{var_name}({','.join(result)})"


def m_query_global(
    backend: GlobalStorageBackend,
    name: str,
    subscripts: tuple[str, ...],
) -> str:
    """Return full reference of next node in depth-first traversal for global variable.

    Args:
        backend: GlobalStorageBackend instance
        name: Global name without caret (e.g., "PATIENT")
        subscripts: Current position subscripts

    Returns:
        Full variable reference string (e.g., "^G(1,2)"), or "" if no more nodes.

    Note:
        Delegates to backend.query() which updates naked indicator.
    """
    return backend.query(name, subscripts)


# =============================================================================
# Phase 5: String function helpers ($PIECE, $EXTRACT - RHS extraction)
# =============================================================================


def m_piece(
    string: str, delimiter: str, from_pos: int, to_pos: int | None = None
) -> str:
    """Extract piece(s) from a delimited string (RHS $PIECE).

    Spec 010 Phase 5 (T027): $PIECE extracts substrings by delimiter position.

    Args:
        string: The string to extract from
        delimiter: The delimiter string
        from_pos: Starting piece number (1-indexed)
        to_pos: Ending piece number (1-indexed, optional - defaults to from_pos)

    Returns:
        The extracted piece(s), or empty string if out of range.
        When extracting a range, pieces are rejoined with the delimiter.

    Examples:
        m_piece("A^B^C", "^", 2) → "B"
        m_piece("A^B^C", "^", 2, 3) → "B^C"
        m_piece("A^B^C", "^", 4) → ""
        m_piece("A::B::C", "::", 2) → "B"

    Note:
        - Piece numbers <= 0 return empty string
        - Multi-character delimiters are supported
        - Empty delimiter returns empty string (edge case)
    """
    # Handle edge cases
    if from_pos <= 0:
        return ""

    if to_pos is None:
        to_pos = from_pos

    # Invalid range
    if to_pos < from_pos:
        return ""

    # Empty delimiter - edge case, return empty
    if not delimiter:
        return ""

    # Split the string by delimiter
    parts = string.split(delimiter)

    # Convert to 0-indexed
    from_idx = from_pos - 1
    to_idx = to_pos - 1

    # Out of range check
    if from_idx >= len(parts):
        return ""

    # Extract the range (clamp to_idx to available parts)
    to_idx = min(to_idx, len(parts) - 1)
    extracted = parts[from_idx : to_idx + 1]

    # Rejoin with delimiter for multi-piece extraction
    return delimiter.join(extracted)


def m_extract(string: str, from_pos: int, to_pos: int) -> str:
    """Extract substring by character position (RHS $EXTRACT).

    Spec 010 Phase 5 (T031): $EXTRACT extracts substrings by position.
    MUMPS uses 1-based indexing with inclusive range.

    Args:
        string: The string to extract from
        from_pos: Starting position (1-indexed)
        to_pos: Ending position (1-indexed, inclusive)

    Returns:
        The extracted substring, or empty string if out of range.

    Examples:
        m_extract("HELLO", 1, 1) → "H"
        m_extract("HELLO", 2, 4) → "ELL"
        m_extract("HELLO", 6, 6) → ""
        m_extract("HELLO", 0, 1) → ""

    Note:
        - Positions <= 0 return empty string
        - from_pos > to_pos returns empty string
        - from_pos > string length returns empty string
    """
    # Handle edge cases
    if from_pos <= 0:
        return ""

    if to_pos < from_pos:
        return ""

    # Convert to 0-indexed
    from_idx = from_pos - 1
    to_idx = to_pos  # Python slice is exclusive, so to_pos is correct

    # Out of range check
    if from_idx >= len(string):
        return ""

    # Extract the substring
    return string[from_idx:to_idx]


def m_find(string: str, target: str, start: int = 1) -> int:
    """Find substring and return position AFTER the match (RHS $FIND).

    Spec 010 Phase 7 (T043): $FIND locates substring and returns position
    AFTER the end of the match. Returns 0 if not found.

    Args:
        string: The string to search in
        target: The substring to find
        start: Starting position for search (1-indexed, default 1)

    Returns:
        Position AFTER the found substring (1-indexed), or 0 if not found.

    Examples:
        m_find("HELLO", "LL") → 5 (position after "LL")
        m_find("HELLO", "L") → 4 (position after first "L")
        m_find("HELLO", "X") → 0 (not found)
        m_find("HELLO", "L", 4) → 5 (search from position 4)
        m_find("ABC", "") → 1 (empty target found at start)

    Note:
        - Returns position AFTER the match, not the start of the match
        - Empty target string returns start position
        - start <= 0 is treated as 1
    """
    # Handle edge cases
    if start <= 0:
        start = 1

    # Empty target returns start position (MUMPS behavior)
    if target == "":
        return start

    # Convert to 0-indexed for search
    start_idx = start - 1

    # If start is beyond string length, not found
    if start_idx >= len(string):
        return 0

    # Find the target starting from start_idx
    pos = string.find(target, start_idx)

    if pos == -1:
        return 0

    # Return position AFTER the match (1-indexed)
    return pos + len(target) + 1


def m_get(
    array: "MArray | None", subscripts: tuple[str, ...], default: str = ""
) -> str:
    """Safe variable retrieval with default value (RHS $GET).

    Spec 010 Phase 6 (T038): $GET returns the value if defined, otherwise the default.
    Distinguished from MArray.get() which always returns "" for undefined.

    Args:
        array: MArray instance or None (undefined variable)
        subscripts: Tuple of subscripts to traverse
        default: Value to return if undefined (default: "")

    Returns:
        The variable's value if defined, otherwise the default value.

    Examples:
        m_get(None, ()) → "" (undefined root)
        m_get(arr, ()) → arr.value if defined
        m_get(arr, ("1",)) → arr[1].value if defined
        m_get(None, (), "DEF") → "DEF" (undefined with default)

    Note:
        $GET distinguishes between undefined and defined-as-empty-string.
        Undefined → returns default
        Defined as "" → returns ""
    """
    if array is None:
        return default

    if not subscripts:
        # Check root value - None means undefined
        if array._value is None:
            return default
        return array._value

    # Traverse subscripts
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
            return default  # Subscript path doesn't exist
        node = node._children[key]

    # Check if this node has a value (None = undefined)
    if node._value is None:
        return default
    return node._value


def m_get_global(
    backend: "GlobalStorageBackend",
    name: str,
    subscripts: tuple[str, ...],
    default: str = "",
) -> str:
    """Safe global variable retrieval with default value (RHS $GET).

    Spec 010 Phase 6 (T039): $GET on global variables.

    Args:
        backend: GlobalStorageBackend instance
        name: Global name without caret (e.g., "PATIENT")
        subscripts: Tuple of subscripts
        default: Value to return if undefined (default: "")

    Returns:
        The variable's value if defined, otherwise the default value.

    Note:
        Delegates to backend.get() which returns None for undefined.
    """
    value = backend.get(name, subscripts)
    if value is None:
        return default
    return value


def _raise_select_false() -> None:
    """Raise SELECTFALSE error for $SELECT with no true condition.

    Spec 010 Phase 3: This function is called as the final fallback in generated
    $SELECT expressions. If all conditions evaluate to false, this raises
    MRuntimeError with the SELECTFALSE error code.

    Raises:
        MRuntimeError: Always raises with code "SELECTFALSE"

    Example generated code:
        # $S(0:"A",0:"B") generates:
        ("A" if m_truth(0) else "B" if m_truth(0) else _raise_select_false())
    """
    from m2py.runtime.exceptions import MRuntimeError

    raise MRuntimeError("SELECTFALSE", "No argument to $SELECT was true")
