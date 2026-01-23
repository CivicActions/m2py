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


def m_format_output(value: Any) -> str:
    """Format a value for MUMPS output.

    MUMPS canonical number formatting:
    - No trailing zeros after decimal point
    - No unnecessary decimal point for integers
    - No leading zero before decimal for values < 1 (0.5 → ".5")
    - Negative numbers keep the minus sign (-0.5 → "-.5")
    - No scientific notation (1E+2 → "100")

    Spec 011 Phase 9: Ensures numeric output matches MUMPS formatting.

    Args:
        value: Any value to format for output

    Returns:
        String formatted according to MUMPS conventions

    Examples:
        m_format_output(1.0) → "1"
        m_format_output(0.5) → ".5"
        m_format_output(-0.5) → "-.5"
        m_format_output(3.14) → "3.14"
        m_format_output(Decimal("1E2")) → "100"
    """
    from decimal import Decimal

    # If not numeric, just convert to string
    if isinstance(value, str):
        return value

    if isinstance(value, bool):
        # Convert boolean to MUMPS 1/0
        return "1" if value else "0"

    # Handle Decimal type (used for large numbers and scientific notation)
    if isinstance(value, Decimal):
        # Check if it's effectively an integer
        if value == int(value):
            return str(int(value))
        # Format without scientific notation
        # Convert to tuple: (sign, digits, exponent)
        sign, digits, exponent = value.as_tuple()
        # Handle special Decimal values (NaN, Infinity) - exponent is a string code
        if not isinstance(exponent, int):
            return str(value)
        # YDB has a limit of ~43 decimal places. Beyond that, output is "0"
        # This prevents memory errors from trying to format 1E-111111111...
        if exponent < -43:
            return "0"
        # Reconstruct the number
        if exponent >= 0:
            # Integer or large number
            return str(int(value))
        else:
            # Decimal number
            int_part = digits[:exponent] if exponent else ()
            frac_part = digits[exponent:]
            int_str = "".join(str(d) for d in int_part) if int_part else ""
            frac_str = "".join(str(d) for d in frac_part)
            # Pad with leading zeros if needed
            if not int_str:
                int_str = ""
                frac_str = "0" * (-exponent - len(digits)) + frac_str
            # Build result
            result = int_str + "." + frac_str
            # Remove trailing zeros
            result = result.rstrip("0").rstrip(".")
            # Remove leading zero before decimal
            if result.startswith("0."):
                result = result[1:]
            if sign:
                result = "-" + result
            return result

    if isinstance(value, (int, float)):
        # Check if it's effectively an integer
        if isinstance(value, float) and value == int(value):
            return str(int(value))

        if isinstance(value, int):
            return str(value)

        # It's a true float with decimals
        s = str(value)

        # Python may output in scientific notation for very large/small numbers
        if "e" in s or "E" in s:
            # Format without scientific notation
            if value == int(value):
                return str(int(value))
            # Use a reasonable number of decimal places
            s = f"{value:.15g}"

        # Remove leading zero before decimal if value is between -1 and 1
        if s.startswith("0."):
            s = s[1:]  # Remove leading zero: "0.5" -> ".5"
        elif s.startswith("-0."):
            s = "-" + s[2:]  # "-0.5" -> "-.5"

        return s

    return str(value)


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
        Per MUMPS spec:
        - If piece_from <= 0 and piece_to <= 0: no modification
        - If piece_from <= 0 and piece_to >= 1: clamp piece_from to 1
        - If piece_from > piece_to: no modification
    """
    # Normalize piece_to: if None, single piece replacement
    if piece_to is None:
        piece_to = piece_from

    # Per MUMPS spec: if piece_from <= 0 and piece_to <= 0, no modification
    # AND the glvn is NOT evaluated (naked indicator not updated)
    if piece_from <= 0 and piece_to <= 0:
        return

    # Per MUMPS spec: if piece_from > piece_to, no modification occurs
    # AND the glvn is NOT evaluated (naked indicator not updated)
    if piece_from > piece_to:
        return

    # Clamp piece_from to 1 if it's <= 0 but piece_to >= 1
    if piece_from <= 0:
        piece_from = 1

    # Get current value (empty string if undefined/None)
    # This is where the glvn is evaluated and naked indicator is updated
    current = var_getter() or ""

    # Handle empty delimiter specially per YDB behavior
    if not delimiter:
        # Empty delimiter: intexpr2=1 replaces entire string, intexpr2>1 appends
        if piece_from == 1:
            var_setter(value)
        else:
            var_setter(current + value)
        return

    # Split by delimiter (preserving all parts)
    parts = current.split(delimiter)

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

    # Per YDB behavior: if from_pos <= 0 AND to_pos <= 0, no modification
    # If from_pos <= 0 but to_pos > 0, treat from_pos as 1
    if from_pos <= 0:
        if to_pos <= 0:
            return  # No-op: both positions are non-positive
        else:
            from_pos = 1  # Treat negative/zero start as 1 when end is positive

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
        m_extract("HELLO", 0, 3) → "HEL" (start treated as 1)
        m_extract("HELLO", -5, 3) → "HEL" (negative start treated as 1)

    Note:
        - from_pos <= 0 is treated as 1 per MUMPS spec
        - to_pos <= 0 returns empty string
        - from_pos > to_pos returns empty string
        - from_pos > string length returns empty string
    """
    # Handle edge cases: to_pos <= 0 means empty result
    if to_pos <= 0:
        return ""

    # Per MUMPS spec: from_pos <= 0 is treated as 1
    if from_pos <= 0:
        from_pos = 1

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


def _is_canonical_numeric(value: str) -> bool:
    """Check if a string is a canonical numeric representation.

    In MUMPS, a canonical number is the shortest representation:
    - No leading zeros (except "0" itself)
    - No trailing zeros after decimal point
    - No unnecessary plus sign

    Args:
        value: String to check

    Returns:
        True if value is canonical numeric representation
    """
    if not value:
        return False
    try:
        num = float(value)
        # Check if string representation matches canonical form
        if num == int(num):
            return value == str(int(num))
        else:
            # For floats, canonical means no trailing zeros
            canonical = str(num)
            return value == canonical
    except (ValueError, TypeError):
        return False


def _format_subscript(value: str) -> str:
    """Format a subscript value for canonical name representation.

    Args:
        value: Subscript value (string)

    Returns:
        Canonically formatted subscript - unquoted for numbers, quoted for strings
    """
    if _is_canonical_numeric(value):
        # Numeric values are not quoted in canonical name
        return value
    else:
        # String values are quoted, with internal quotes doubled
        escaped = value.replace('"', '""')
        return f'"{escaped}"'


def m_name(
    var_name: str,
    subscripts: tuple[str, ...],
    depth: int | None = None,
    is_global: bool = False,
) -> str:
    """Convert variable reference to canonical name string ($NAME).

    Spec 010 Phase 9 (T059): Implements $NAME intrinsic function.

    Args:
        var_name: Variable name (without caret for globals)
        subscripts: Tuple of subscript values (as strings)
        depth: Number of subscripts to include (None = all, 0 = name only)
        is_global: True if this is a global variable (prepend ^)

    Returns:
        Canonical name string like "A(1,2,3)" or "^GLO(1,2)"

    Examples:
        m_name("A", ("1", "2", "3")) → "A(1,2,3)"
        m_name("A", ("1", "2", "3"), depth=2) → "A(1,2)"
        m_name("A", ("1", "2", "3"), depth=0) → "A"
        m_name("GLO", ("1", "2"), is_global=True) → "^GLO(1,2)"
        m_name("A", ("foo", "bar")) → 'A("foo","bar")'
    """
    # Apply depth limit if specified
    if depth is not None:
        # depth >= len(subscripts) means use all subscripts
        if depth < len(subscripts):
            subscripts = subscripts[:depth]

    # Build the canonical name
    prefix = "^" if is_global else ""
    if not subscripts:
        return f"{prefix}{var_name}"

    # Format each subscript (numeric = unquoted, string = quoted)
    formatted_subs = [_format_subscript(sub) for sub in subscripts]
    return f"{prefix}{var_name}({','.join(formatted_subs)})"


def m_qlength(name: str) -> int:
    """Count subscripts in a name string ($QLENGTH).

    Spec 010 Phase 9 (T060): Implements $QLENGTH intrinsic function.

    Args:
        name: Canonical name string like "A(1,2,3)" or "^GLO(1,2)"

    Returns:
        Number of subscripts (0 if no subscripts)

    Examples:
        m_qlength("A") → 0
        m_qlength("A(1,2,3)") → 3
        m_qlength("^GLO(1,2)") → 2
        m_qlength('A("hello","world")') → 2

    Note:
        Empty string input raises NOCANONICNAME in YottaDB.
        For simplicity, we return 0 for empty strings.
    """
    if not name or "(" not in name:
        return 0

    # Find the opening paren
    paren_pos = name.index("(")
    if paren_pos == len(name) - 1:
        return 0

    # Parse the subscript portion
    subscript_part = name[paren_pos + 1 : -1]  # Remove outer parens
    if not subscript_part:
        return 0

    # Count subscripts, handling quoted strings with commas
    count = 0
    in_quote = False
    i = 0
    while i < len(subscript_part):
        ch = subscript_part[i]
        if ch == '"':
            if (
                in_quote
                and i + 1 < len(subscript_part)
                and subscript_part[i + 1] == '"'
            ):
                # Escaped quote - skip both
                i += 2
                continue
            in_quote = not in_quote
        elif ch == "," and not in_quote:
            count += 1
        i += 1

    # Number of subscripts is number of commas + 1
    return count + 1


def m_qsubscript(name: str, position: int) -> str:
    """Extract subscript from name string ($QSUBSCRIPT).

    Spec 010 Phase 9 (T061): Implements $QSUBSCRIPT intrinsic function.

    Args:
        name: Canonical name string like "A(1,2,3)"
        position: Subscript position (0 = variable name, 1+ = subscripts)

    Returns:
        The subscript value (unquoted), or empty string if out of range.
        Position 0 returns the variable name (with ^ for globals).

    Examples:
        m_qsubscript("A(1,2,3)", 0) → "A"
        m_qsubscript("A(1,2,3)", 1) → "1"
        m_qsubscript("A(1,2,3)", 3) → "3"
        m_qsubscript("A(1,2,3)", 5) → ""
        m_qsubscript("^GLO(1,2)", 0) → "^GLO"
        m_qsubscript('A("hello",2)', 1) → "hello"

    Note:
        Negative positions return empty string.
    """
    if position < 0:
        return ""

    # Position 0 returns the variable name (with ^ for globals)
    paren_pos = name.find("(")
    if position == 0:
        if paren_pos == -1:
            return name
        return name[:paren_pos]

    # No subscripts in name
    if paren_pos == -1 or paren_pos == len(name) - 1:
        return ""

    # Parse subscripts
    subscript_part = name[paren_pos + 1 : -1]  # Remove outer parens
    if not subscript_part:
        return ""

    # Extract the subscript at the given position (1-indexed)
    subscripts: list[str] = []
    current = ""
    in_quote = False
    i = 0
    while i < len(subscript_part):
        ch = subscript_part[i]
        if ch == '"':
            if not in_quote:
                in_quote = True
                # Don't include the opening quote in the value
            elif i + 1 < len(subscript_part) and subscript_part[i + 1] == '"':
                # Escaped quote - include one quote
                current += '"'
                i += 2
                continue
            else:
                in_quote = False
                # Don't include the closing quote in the value
        elif ch == "," and not in_quote:
            subscripts.append(current)
            current = ""
        else:
            current += ch
        i += 1

    # Add the last subscript
    subscripts.append(current)

    # Return the requested subscript (1-indexed)
    if position > len(subscripts):
        return ""
    return subscripts[position - 1]


def m_justify(value: float, width: int, decimals: int) -> str:
    """Right-justify a numeric value with decimal formatting ($JUSTIFY).

    Spec 010 Phase 10 (T067): Implements 3-argument $JUSTIFY.

    Args:
        value: Numeric value to format
        width: Field width to right-justify within
        decimals: Number of decimal places

    Returns:
        Right-justified string with specified decimal places

    Examples:
        m_justify(3.14159, 10, 2) → "      3.14"
        m_justify(42, 5, 0) → "   42"
    """
    # Format with specified decimal places
    formatted = f"{value:.{decimals}f}"
    # Right-justify within width
    return formatted.rjust(width)


def m_fnumber(value: float, codes: str, decimals: int | None = None) -> str:
    """Format number with specified formatting codes ($FNUMBER).

    Spec 010 Phase 10 (T069): Implements $FNUMBER intrinsic function.

    Formatting codes (can be combined):
    - "," = add comma separators for thousands
    - "+" = show + sign for positive numbers
    - "-" = suppress the minus sign on negative values
    - "P" = parentheses for negative, space padding for positive
    - "T" = trailing sign (trailing space for positive, - for negative)

    Args:
        value: Numeric value to format
        codes: String of formatting codes
        decimals: Number of decimal places (optional)

    Returns:
        Formatted number string

    Examples:
        m_fnumber(12345.67, ",") → "12,345.67"
        m_fnumber(-42, "P") → "(42)"
        m_fnumber(42, "+") → "+42"
        m_fnumber(-42, "-") → "42"
        m_fnumber(42, "T") → "42 "
        m_fnumber(-42, "T") → "42-"
    """
    codes_upper = codes.upper()

    # Handle decimals first
    if decimals is not None:
        value = round(value, decimals)

    # Determine if value is negative
    is_negative = value < 0
    abs_value = abs(value)

    # Format the number (without sign initially)
    if decimals is not None:
        formatted = f"{abs_value:.{decimals}f}"
    else:
        # MUMPS preserves decimal precision from input
        if abs_value == int(abs_value):
            formatted = str(int(abs_value))
        else:
            formatted = str(abs_value)

    # Add comma separators if requested
    if "," in codes_upper:
        # Split by decimal point
        parts = formatted.split(".")
        # Add commas to integer part
        int_part = parts[0]
        int_with_commas = ""
        for i, digit in enumerate(reversed(int_part)):
            if i > 0 and i % 3 == 0:
                int_with_commas = "," + int_with_commas
            int_with_commas = digit + int_with_commas
        if len(parts) > 1:
            formatted = int_with_commas + "." + parts[1]
        else:
            formatted = int_with_commas

    # Handle sign formatting based on codes
    # Priority: P > - > T > + > default
    if "P" in codes_upper:
        # Parentheses for negative, space padding for positive
        if is_negative:
            return f"({formatted})"
        else:
            return f" {formatted} "
    elif "-" in codes_upper:
        # Suppress the minus sign on negative values (return absolute value)
        return formatted
    elif "T" in codes_upper:
        # Trailing sign: space for positive, - for negative
        if is_negative:
            return f"{formatted}-"
        else:
            return f"{formatted} "
    elif "+" in codes_upper:
        # Force + sign for positive
        if is_negative:
            return f"-{formatted}"
        else:
            return f"+{formatted}"
    else:
        # Default: leading minus for negative
        if is_negative:
            return f"-{formatted}"
        else:
            return formatted


# =============================================================================
# Spec 011: String Comparison Operators
# =============================================================================

# Note: Contains ([) and Follows (]) operators are inlined in codegen as:
#   Contains: int(str(right) in str(left))
#   Follows:  int(str(left) > str(right))
# Only sorts-after (]]) requires a runtime helper due to MUMPS collation.


def m_sorts_after(left: Any, right: Any) -> int:
    """Check if left strictly sorts after right (MUMPS ]] operator).

    MUMPS semantics: A]]B returns 1 if A strictly collates after B using
    MUMPS collation order (numerics before strings). Empty string never
    sorts after anything.

    Note: This differs from the ] (follows) operator which uses simple
    ASCII string comparison. The ]] operator uses MUMPS collation where:
    - Numeric values (including numeric strings) sort before non-numeric strings
    - Numeric values are compared numerically (10 > 9)
    - Non-numeric strings are compared by ASCII/UTF-8 ordering

    Args:
        left: Left operand
        right: Right operand

    Returns:
        1 if left is non-empty and left sorts after right in MUMPS collation,
        0 otherwise

    Examples:
        >>> m_sorts_after("B", "A")
        1
        >>> m_sorts_after("", "A")
        0
        >>> m_sorts_after("A", "B")
        0
        >>> m_sorts_after(10, 9)
        1
        >>> m_sorts_after("10", "9")
        1
        >>> m_sorts_after("ABC", "9")
        1
    """
    # Empty string never sorts after anything
    left_str = str(left)
    if left_str == "":
        return 0

    # Use MUMPS collation comparison
    left_key = _mumps_collation_key(left)
    right_key = _mumps_collation_key(right)
    return int(left_key > right_key)


# =============================================================================
# Spec 011: Pattern Match Operator
# =============================================================================


def m_pattern_match(string: Any, pattern: str) -> int:
    """Match string against MUMPS pattern (MUMPS ? operator).

    This runtime helper is used only for **indirect patterns** (X?@Y) where
    the pattern is determined at runtime. For direct/literal patterns (X?1A.N),
    codegen inlines a pre-compiled regex via re.fullmatch() for better performance.

    Uses compile_pattern_to_regex() from analysis module to convert
    MUMPS pattern to Python regex, then performs fullmatch.

    Args:
        string: String to match
        pattern: MUMPS pattern string (e.g., "1A.N", "3N")

    Returns:
        1 if string matches pattern, 0 otherwise

    Examples:
        >>> m_pattern_match("ABC", "1A.A")
        1
        >>> m_pattern_match("123", "3N")
        1
        >>> m_pattern_match("12A", "3N")
        0
    """
    import re

    from m2py.analysis.pattern_compiler import compile_pattern_to_regex

    try:
        regex = compile_pattern_to_regex(pattern)
        # Use DOTALL for E pattern code to match newlines
        result = re.fullmatch(regex, str(string), re.DOTALL)
        return 1 if result else 0
    except Exception:
        # Pattern compilation error - return 0 (no match)
        return 0


# =============================================================================
# Spec 011: NEW Command Scope Management
# =============================================================================


# Sentinel value to indicate a variable was undefined before NEW
_UNDEFINED = object()


class NewScopeManager:
    """Context manager for MUMPS NEW command scope semantics.

    MUMPS NEW command creates a new scope level for specified variables,
    hiding the caller's values. When the function returns, the original
    values are restored.

    Usage in generated code:
        with NewScopeManager(_scope) as _new_mgr:
            _new_mgr.new_var('X')  # N X - saves and removes X
            _scope['X'] = MArray()
            _scope['X'].value = 999
            # ... rest of function body ...
        # On exit: X restored to original value

    This handles:
    - Save original value (or mark as undefined)
    - Remove variable from scope (making it undefined)
    - Restore original values on normal return or exception

    Example MUMPS:
        CALLER
         S X=100
         D ^CALLEE
         W X  ; Prints 100 - X restored after callee's NEW

        CALLEE
         N X
         S X=999
         W X  ; Prints 999
         Q

    Generated Python for CALLEE:
        def CALLEE(_rt, _scope=None, **_kwargs):
            _scope = _scope if _scope is not None else {}
            with NewScopeManager(_scope) as _new_mgr:
                _new_mgr.new_var('X')
                _scope['X'] = MArray()
                _scope['X'].value = 999
                _rt.write(_scope.get('X', MArray()).value or '')
                return
    """

    def __init__(self, scope: dict):
        """Initialize the scope manager.

        Args:
            scope: The _scope dict for the current routine
        """
        self._scope = scope
        self._saved: dict = {}

    def __enter__(self) -> "NewScopeManager":
        """Enter the context - nothing to do on entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context - restore all saved variables.

        This runs on both normal return and exceptions, ensuring
        MUMPS NEW semantics are preserved.
        """
        for var_name, saved_value in self._saved.items():
            # Check if this is a special variable (stored as tuple with setter)
            if var_name.startswith("__special__"):
                # Special variable: saved_value is (value, setter)
                value, setter = saved_value
                setter(value)
            elif saved_value is _UNDEFINED:
                # Variable was undefined before NEW - remove it
                self._scope.pop(var_name, None)
            else:
                # Variable had a value - restore it
                self._scope[var_name] = saved_value

    def new_var(self, var_name: str) -> None:
        """NEW a single variable - save and remove from scope.

        If the variable has already been NEWed in this scope level,
        this is a no-op (first NEW wins).

        Args:
            var_name: The MUMPS variable name (not translated)
        """
        if var_name in self._saved:
            # Already NEWed - skip
            return

        # Save current value (or mark as undefined)
        if var_name in self._scope:
            self._saved[var_name] = self._scope[var_name]
            del self._scope[var_name]
        else:
            self._saved[var_name] = _UNDEFINED

    def new_special_var(
        self, name: str, current_value: str, setter: "Callable[[str], None]"
    ) -> None:
        """NEW a special variable like $ETRAP or $ECODE.

        Spec 013 Phase 12: Handles NEW for special variables that use
        runtime setters instead of _scope storage.

        VistA pattern: N $ETRAP,$ESTACK S $ETRAP="D ERR^ROUTINE"
        This saves the current $ETRAP value and restores it on scope exit.

        Args:
            name: Identifier for this special var (for dedup check)
            current_value: Current value to save
            setter: Function to call with saved value on restore
        """
        # Use special key prefix to avoid collision with regular vars
        key = f"__special__{name}"
        if key in self._saved:
            # Already NEWed - skip
            return

        # Store tuple of (value, setter) - we'll call setter(value) on restore
        self._saved[key] = (current_value, setter)
        # Initialize to empty (NEW semantics)
        setter("")


# =============================================================================
# READ Command Helpers (Spec 011 Phase 20)
# =============================================================================


def m_read_timeout(timeout_seconds: float) -> tuple[str, int]:
    """Read input with timeout.

    Attempts to read a line from stdin with a timeout.
    If input is received within the timeout, returns the input and sets
    $TEST to 1. If timeout occurs, returns empty string and sets $TEST to 0.

    MUMPS semantics:
    - R X:n reads with n-second timeout
    - On success: X gets input, $TEST=1
    - On timeout: X gets empty string, $TEST=0

    Args:
        timeout_seconds: Maximum seconds to wait for input

    Returns:
        Tuple of (input_value, test_flag)
        test_flag is 1 for success, 0 for timeout
    """
    import select
    import sys

    timeout = float(timeout_seconds)

    # Check if stdin has data available within timeout
    # select.select returns (readable, writable, exceptional) lists
    readable, _, _ = select.select([sys.stdin], [], [], timeout)

    if readable:
        # Input available - read it
        line = sys.stdin.readline()
        # Strip trailing newline if present
        if line.endswith("\n"):
            line = line[:-1]
        return (line, 1)
    else:
        # Timeout occurred
        return ("", 0)


def m_read_char() -> str:
    """Read a single character from stdin.

    MUMPS R *X reads a single character and stores its ASCII value.
    For simplicity, we return the character as a string (code can convert
    to ASCII if needed with $ASCII).

    Returns:
        Single character read from stdin, or empty string on EOF
    """
    import sys

    char = sys.stdin.read(1)
    return char
