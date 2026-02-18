"""Runtime helper functions for MUMPS special operations.

Provides helper functions for operations that cannot be expressed
as simple Python expressions:

- m_set_piece: LHS $PIECE assignment (S $P(X,"^",2)="NEW")
- m_set_extract: LHS $EXTRACT assignment (S $E(X,2,3)="XX")
- m_data: $DATA function for local arrays
- m_data_global: $DATA function for global variables
- m_order: $ORDER function for local arrays
- m_order_global: $ORDER function for global variables
- m_query: $QUERY function for local arrays
- m_query_global: $QUERY function for global variables
- m_var_value: Extract scalar value from either MArray or plain value

These helpers are imported in generated code and called at runtime.
"""

from __future__ import annotations

import os
import subprocess
import warnings
from decimal import Decimal, ROUND_HALF_UP, localcontext
from typing import TYPE_CHECKING, Any, Callable, Tuple

from m2py.core.subscripts import SubscriptCanonicalizer

if TYPE_CHECKING:
    from m2py.runtime import MArray
    from m2py.runtime.globals import GlobalStorageBackend


def m_var_value(val: Any) -> Any:
    """Extract scalar value from either an MArray or plain value.

    When variables are passed between routines, they may be:
    1. MArray objects (from the calling routine's _scope with MArray default)
    2. Plain values (from TRAMPOLINE routines that return state.VAR directly)

    This function handles both cases uniformly.

    Args:
        val: Either an MArray object or a plain value (str, int, etc.)

    Returns:
        The scalar value (MArray.value if MArray, else the value itself)

    Examples:
        >>> m_var_value(MArray("hello"))
        'hello'
        >>> m_var_value("world")
        'world'
        >>> m_var_value(MArray())  # Undefined MArray
        ''
        >>> m_var_value(None)
        ''
    """
    # Handle MArray by extracting .value
    if hasattr(val, "value"):
        return val.value
    # Handle None as empty string (MUMPS undefined = empty string)
    if val is None:
        return ""
    # Plain values pass through
    return val


def _canonicalize_subscript(sub: Any) -> str:
    """Canonicalize a subscript value for consistent MArray lookup.

    Uses SubscriptCanonicalizer for proper MUMPS subscript canonicalization
    so that A(1), A(1.0), and A("1") all access the same node.

    Args:
        sub: Subscript value (int, float, Decimal, str, etc.)

    Returns:
        Canonical string representation
    """
    return SubscriptCanonicalizer.canonicalize(sub)


def _mumps_collation_key(value: Any) -> Tuple[int, Any]:
    """Generate a sort key for MUMPS collation order.

    MUMPS collation order:
    1. Numeric values (sorted numerically, negatives first)
    2. String values (sorted by ASCII/UTF-8)

    The key returns a tuple (type_order, sort_value) where:
    - type_order: 0 for numeric, 1 for string
    - sort_value: the value to compare within the type

    CRITICAL: Only CANONICAL numeric strings collate as numbers.
    Non-canonical numeric strings like "-4.", "-4.0", ".0", "01" collate as strings.

    Args:
        value: A subscript value (string, int, float, or Decimal)

    Returns:
        Tuple for comparison in sorted()
    """
    from m2py.core.subscripts import SubscriptCanonicalizer

    # Check if value is numeric (can be int, float, Decimal, or numeric string)
    if isinstance(value, (int, float, Decimal)):
        return (0, float(value))

    # For strings, only canonical numeric strings collate as numbers
    if isinstance(value, str):
        # Check if string is a CANONICAL numeric form
        if SubscriptCanonicalizer.is_canonical_numeric_string(value):
            # It's canonical, collate as number
            num = Decimal(value)
            return (0, float(num))
        # Non-canonical or non-numeric strings collate as strings
        return (1, value)

    return (1, str(value))


def m_format_output(value: Any) -> str:
    """Format a value for MUMPS output.

    MUMPS canonical number formatting:
    - No trailing zeros after decimal point
    - No unnecessary decimal point for integers
    - No leading zero before decimal for values < 1 (0.5 → ".5")
    - Negative numbers keep the minus sign (-0.5 → "-.5")
    - No scientific notation (1E+2 → "100")

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
        m_format_output("0.5") → "0.5"  # Strings pass through unchanged
    """
    from decimal import Decimal

    # Handle MArray objects by extracting their value
    # This is needed for TRAMPOLINE strategy where state._locals contains MArrays
    # and _rt.write(state._locals.get('V', '')) passes MArray objects
    if hasattr(value, "value"):
        return m_format_output(value.value)

    # If the value is a Python string, return it as-is.
    # In MUMPS, strings preserve their exact content - they are NOT canonicalized.
    # Only numeric types (Decimal, int, float) are canonicalized on output.
    # Example: S X="1212.000" W X → outputs "1212.000" (string preserved)
    #          S X=1212.000 W X → outputs "1212" (numeric canonicalized)
    if isinstance(value, str):
        return value

    # Handle Decimal type (used for large numbers and scientific notation)
    if isinstance(value, Decimal):
        # Check if it's effectively an integer
        if value == int(value):
            return str(int(value))
        # Format without scientific notation
        # Convert to tuple: (sign, digits, exponent)
        sign, digits, exponent = value.as_tuple()
        # YDB has a limit of ~43 decimal places. Beyond that, output is "0"
        # This prevents memory errors from trying to format 1E-111111111...
        if not isinstance(exponent, int) or exponent < -43:
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


def m_data(array: MArray | None, subscripts: tuple[Any, ...] = ()) -> int:
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
        # Canonicalize subscript for consistent lookup
        key = _canonicalize_subscript(sub)
        if key not in node._children:
            return 0
        node = node._children[key]
    return node.data()


def m_data_global(
    backend: GlobalStorageBackend,
    name: str,
    subscripts: tuple[Any, ...],
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
    subscripts: tuple[Any, ...],
    direction: Any = 1,
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

    # Coerce direction to int (may come from MUMPS expression as string/Decimal)
    if not isinstance(direction, int):
        direction = (
            int(Decimal(str(direction)))
            if str(direction).lstrip("-").replace(".", "", 1).isdigit()
            else 1
        )

    # Navigate to parent level (all but last subscript)
    # The last subscript is the starting point for the search
    if not subscripts:
        return ""

    parent_subs = subscripts[:-1]
    start_key = subscripts[-1]

    # Navigate to parent node
    node = array
    for sub in parent_subs:
        # Canonicalize subscript for consistent lookup
        key = _canonicalize_subscript(sub)
        if key not in node._children:
            return ""
        node = node._children[key]

    # Get all children keys sorted in MUMPS collation order
    keys = sorted(node._children.keys(), key=_mumps_collation_key)

    if direction == -1:
        keys = list(reversed(keys))

    # Canonicalize start_key for comparison
    start_key_canonical = _canonicalize_subscript(start_key) if start_key != "" else ""

    if start_key_canonical == "":
        # Empty string means get first key in the current direction
        return m_format_output(keys[0]) if keys else ""

    # Find the next key after start_key
    # First, locate start_key in the sorted list
    start_sort_key = _mumps_collation_key(start_key_canonical)

    for key in keys:
        key_sort = _mumps_collation_key(key)
        if direction == 1:
            # Forward: find first key greater than start_key
            if key_sort > start_sort_key:
                return m_format_output(key)
        else:
            # Reverse: find first key less than start_key
            if key_sort < start_sort_key:
                return m_format_output(key)

    return ""


def m_order_global(
    backend: GlobalStorageBackend,
    name: str,
    subscripts: tuple[Any, ...],
    direction: Any = 1,
    update_naked: bool = True,
) -> str:
    """Return next subscript in MUMPS collation order for global variable.

    Args:
        backend: GlobalStorageBackend instance
        name: Global name without caret (e.g., "PATIENT")
        subscripts: Tuple of subscript values. Last element is starting point.
        direction: 1 for forward, -1 for reverse (coerced from string/Decimal)
        update_naked: If True, update the naked indicator (default).
            If False, skip naked update (caller pre-set it).

    Returns:
        Next/previous subscript as string, or "" if no more subscripts.

    Note:
        Delegates to backend.order() which optionally updates naked indicator.
        Direction is coerced to int via m_num() to handle string/Decimal values
        from evaluated MUMPS expressions.
    """
    if not isinstance(direction, int):
        direction = (
            int(Decimal(str(direction)))
            if str(direction).lstrip("-").replace(".", "", 1).isdigit()
            else 1
        )
    return backend.order(name, subscripts, direction, update_naked=update_naked)


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
    subscripts: tuple,
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
        m_query(arr, "A", (1, 1)) → "A(1,2)"
        m_query(arr, "A", (1, 2)) → "A(2,1)"
        m_query(arr, "A", (2, 1)) → ""
    """
    if array is None:
        return ""

    # Canonicalize subscripts to strings for comparison
    canon_subs = tuple(_canonicalize_subscript(s) for s in subscripts)

    # Check if we're starting from empty string (find first valued node)
    if canon_subs == ("",) or canon_subs == ():
        # Start from beginning - find first valued node in entire tree
        result = _find_next_valued_node(array, [], (), at_start=True)
    else:
        # Find next valued node after the given subscripts
        result = _find_next_valued_node(array, [], canon_subs, at_start=False)

    if result is None:
        return ""

    # Format as variable reference: "A(1,2,3)" with proper quoting
    if len(result) == 0:
        return var_name
    formatted_subs = [_format_subscript(sub) for sub in result]
    return f"{var_name}({','.join(formatted_subs)})"


def m_query_global(
    backend: GlobalStorageBackend,
    name: str,
    subscripts: tuple[Any, ...],
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
# String function helpers ($PIECE, $EXTRACT - RHS extraction)
# =============================================================================


def m_piece(
    string: str, delimiter: str, from_pos: int, to_pos: int | None = None
) -> str:
    """Extract piece(s) from a delimited string (RHS $PIECE).

    $PIECE extracts substrings by delimiter position.

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
        m_piece("A^B^C", "^", -1, 2) → "A^B" (negative from_pos clamps to 1)
        m_piece("A^B^C", "^", 0, 2) → "A^B" (zero from_pos clamps to 1)

    Note:
        - Single-arg piece numbers <= 0 return empty string
        - Range with from_pos <= 0 but valid to_pos clamps from_pos to 1
        - Multi-character delimiters are supported
        - Empty delimiter returns empty string (edge case)
    """
    if to_pos is None:
        to_pos = from_pos
        # Single piece: positions <= 0 return empty string
        if from_pos <= 0:
            return ""
    else:
        # Range extraction: clamp from_pos to 1 if <= 0
        if from_pos <= 0:
            from_pos = 1

    # Invalid range (to_pos < from_pos after clamping)
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

    $EXTRACT extracts substrings by position.
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

    $FIND locates substring and returns position
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
    array: "MArray | None", subscripts: tuple[Any, ...], default: str = ""
) -> str:
    """Safe variable retrieval with default value (RHS $GET).

    $GET returns the value if defined, otherwise the default.
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
        # Canonicalize subscript for consistent lookup
        key = _canonicalize_subscript(sub)
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
    subscripts: tuple[Any, ...],
    default: str = "",
    update_naked: bool = True,
) -> str:
    """Safe global variable retrieval with default value (RHS $GET).

    $GET on global variables.

    Args:
        backend: GlobalStorageBackend instance
        name: Global name without caret (e.g., "PATIENT")
        subscripts: Tuple of subscripts
        default: Value to return if undefined (default: "")
        update_naked: If True, update the naked indicator (default).
            If False, skip naked update (caller pre-set it).

    Returns:
        The variable's value if defined, otherwise the default value.

    Note:
        Delegates to backend.get() which returns None for undefined.
    """
    value = backend.get(name, subscripts, update_naked=update_naked)
    if value is None:
        return default
    return value


def m_increment(
    array: "MArray | None",
    subscripts: tuple[Any, ...],
    increment: str = "1",
    scope: dict | None = None,
    var_name: str = "",
) -> str:
    """$INCREMENT for local variables.

    Atomically reads, increments, and writes back a local variable.
    If undefined, treats as 0 before incrementing.

    Args:
        array: MArray instance or None (undefined variable)
        subscripts: Tuple of subscript values to navigate
        increment: Amount to increment by (default "1")
        scope: The _scope dict to create the variable in if needed
        var_name: Python-translated variable name (for creating in scope)

    Returns:
        New value after increment (as canonical MUMPS string)
    """
    from m2py.core.values import m_num, m_str
    from m2py.runtime import MArray as MArrayClass

    # Ensure the variable exists in scope
    if array is None and scope is not None and var_name:
        array = MArrayClass()
        scope[var_name] = array

    if array is None:
        # Can't write back without scope — just compute
        result = m_num(increment)
        return m_str(result)

    # Navigate to target node, creating path if needed
    node = array
    for sub in subscripts:
        key = _canonicalize_subscript(sub)
        if key not in node._children:
            node._children[key] = MArrayClass()
        node = node._children[key]

    # Get current value (None → 0)
    current = node._value if node._value is not None else "0"

    # MUMPS numeric addition
    result = m_num(current) + m_num(increment)  # type: ignore[operator]

    # Normalize: integer if whole number
    if isinstance(result, float) and result == int(result):
        result = int(result)

    result_str = m_str(result)
    node._value = result_str
    return result_str


def m_increment_global(
    backend: "GlobalStorageBackend",
    name: str,
    subscripts: tuple[Any, ...],
    increment: str = "1",
) -> str:
    """$INCREMENT for global variables.

    Delegates to the backend's atomic incr() method.

    Args:
        backend: GlobalStorageBackend instance
        name: Global name without caret
        subscripts: Tuple of subscript values
        increment: Amount to increment by (default "1")

    Returns:
        New value after increment (as canonical MUMPS string)
    """
    return backend.incr(name, subscripts, increment)


def _raise_select_false() -> None:
    """Raise SELECTFALSE error for $SELECT with no true condition.

    This function is called as the final fallback in generated
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
    """Check if a string is a canonical MUMPS numeric representation.

    In MUMPS, a canonical number is the shortest representation:
    - No leading zeros (except "0" itself or "0.xxx")
    - No trailing zeros after decimal point
    - No unnecessary plus sign
    - No decimal point without fractional part
    - Fractions < 1 have no leading zero: ".5" not "0.5"
    - Negative fractions: "-.5" not "-0.5"

    Uses m_str() for canonical comparison to ensure consistency with
    the transpiler's number formatting.

    Args:
        value: String to check

    Returns:
        True if value is canonical numeric representation
    """
    from m2py.core.values import m_str

    if not value:
        return False
    try:
        # Use Decimal to avoid float precision loss
        dec = Decimal(value)
        # Reject non-finite values (Infinity, NaN, sNaN)
        if not dec.is_finite():
            return False
        # Use sufficient precision for very long decimals
        with localcontext() as ctx:
            ctx.prec = max(ctx.prec, len(value) + 10)
            dec = Decimal(value)
            canonical = m_str(dec)
        return value == canonical
    except Exception:
        return False


def _format_subscript(value) -> str:
    """Format a subscript value for canonical name representation.

    Args:
        value: Subscript value (any type - will be canonicalized)

    Returns:
        Canonically formatted subscript - unquoted for numbers, quoted for strings
    """
    # First canonicalize numeric types to string
    canonical = _canonicalize_subscript(value)

    if _is_canonical_numeric(canonical):
        # Numeric values are not quoted in canonical name
        return canonical
    else:
        # String values are quoted, with internal quotes doubled
        escaped = canonical.replace('"', '""')
        return f'"{escaped}"'


def m_name(
    var_name: str,
    subscripts: tuple,
    depth: int | None = None,
    is_global: bool = False,
) -> str:
    """Convert variable reference to canonical name string ($NAME).

    Implements the $NAME intrinsic function.

    Args:
        var_name: Variable name (without caret for globals)
        subscripts: Tuple of subscript values (any type - will be canonicalized)
        depth: Number of subscripts to include (None = all, 0 = name only)
        is_global: True if this is a global variable (prepend ^)

    Returns:
        Canonical name string like "A(1,2,3)" or "^GLO(1,2)"

    Examples:
        m_name("A", (1, 2, 3)) → "A(1,2,3)"
        m_name("A", (1, 2, 3), depth=2) → "A(1,2)"
        m_name("A", (1, 2, 3), depth=0) → "A"
        m_name("GLO", (1, 2), is_global=True) → "^GLO(1,2)"
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

    Implements the $QLENGTH intrinsic function.

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

    Implements the $QSUBSCRIPT intrinsic function.

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


def m_justify(value: int | float | Decimal, width: int, decimals: int) -> str:
    """Right-justify a numeric value with decimal formatting ($JUSTIFY).

    Implements 3-argument $JUSTIFY.

    Uses ROUND_HALF_UP (traditional rounding) per MUMPS spec, not
    ROUND_HALF_EVEN (banker's rounding) which Python's Decimal default uses.

    Args:
        value: Numeric value to format
        width: Field width to right-justify within
        decimals: Number of decimal places

    Returns:
        Right-justified string with specified decimal places

    Examples:
        m_justify(3.14159, 10, 2) → "      3.14"
        m_justify(42, 5, 0) → "   42"
        m_justify(123.45, 7, 1) → "  123.5" (ROUND_HALF_UP, not 123.4)
    """
    # Convert to Decimal for precise rounding
    if isinstance(value, Decimal):
        dec_value = value
    else:
        dec_value = Decimal(str(value))

    # Create quantizer for specified decimal places (e.g., "0.1" for 1 decimal)
    if decimals > 0:
        quantizer = Decimal("1." + "0" * decimals)
    else:
        quantizer = Decimal("1")

    # Round using ROUND_HALF_UP (traditional rounding)
    rounded = dec_value.quantize(quantizer, rounding=ROUND_HALF_UP)

    # Format with specified decimal places
    if decimals > 0:
        formatted = f"{rounded:.{decimals}f}"
    else:
        formatted = str(int(rounded))

    # Right-justify within width
    return formatted.rjust(width)


def m_fnumber(
    value: "int | float | Decimal", codes: str, decimals: int | None = None
) -> str:
    """Format number with specified formatting codes ($FNUMBER).

    Implements the $FNUMBER intrinsic function.
    Composes format codes correctly per ANSI spec.

    Format codes (composable):
    - "," = add comma separators for thousands
    - "+" = force + sign for positive (zero gets no sign)
    - "-" = suppress minus sign on negative values
    - "P" = parentheses for negative, space padding for positive
    - "T" = trailing sign position

    Composition rules:
    - T and - compose: T moves sign to trailing position, - suppresses minus
    - T and + compose: T moves sign to trailing, + forces sign for positive
    - + and - compose: positive gets +, negative gets no sign
    - P is exclusive (cannot combine with +, -, T)

    Number formatting rules:
    - 2-arg form: uses MUMPS canonical format (no leading zero for .xx)
    - 3-arg form: always shows leading zero (0.xx)

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
        m_fnumber(-20, "T-") → "20 "
    """
    from m2py.core.values import m_str

    codes_upper = codes.upper()

    # Step 1: Convert to Decimal for precision
    if isinstance(value, Decimal):
        dec_value = value
    elif isinstance(value, float):
        # Use string representation to avoid float precision issues
        dec_value = Decimal(str(value))
    else:
        dec_value = Decimal(value)

    # Step 2: Handle rounding when decimals specified
    if decimals is not None:
        if decimals >= 0:
            quantizer = Decimal(10) ** (-decimals)
            # Use enough precision to hold all integer digits + requested decimal places
            exp = dec_value.as_tuple().exponent
            exp_int = exp if isinstance(exp, int) else 0
            needed = len(dec_value.as_tuple().digits) + abs(exp_int) + decimals + 2
            with localcontext() as ctx:
                ctx.prec = max(ctx.prec, needed)
                dec_value = dec_value.quantize(quantizer, rounding=ROUND_HALF_UP)
        else:
            # Negative decimals: round to left of decimal point
            dec_value = dec_value  # MUMPS treats negative decimals as 0 places

    # Step 3: Determine sign
    is_negative = dec_value < 0
    is_zero = dec_value == 0
    abs_value = dec_value.copy_abs()  # copy_abs avoids context-dependent truncation

    # Step 4: Format the absolute value string
    if decimals is not None:
        # 3-arg form: fixed decimal places with leading zero
        if decimals <= 0:
            formatted = str(int(abs_value))
        else:
            # Format via Decimal to avoid float precision loss on large numbers
            # After quantize, abs_value already has correct decimal places
            sign, digits, exponent = abs_value.as_tuple()
            # Narrow exponent type (can be str for NaN/Inf, but those won't reach here)
            exp = exponent if isinstance(exponent, int) else 0
            # Build the full digit string
            digit_str = "".join(str(d) for d in digits)
            # exponent is negative (e.g. -4 means 4 decimal places)
            if exp < 0:
                dec_places = -exp
                if len(digit_str) <= dec_places:
                    # Need leading zeros: e.g. digits=(5,) exp=-4 → "0.0005"
                    digit_str = digit_str.zfill(dec_places + 1)
                int_part = digit_str[: len(digit_str) - dec_places] or "0"
                frac_part = digit_str[len(digit_str) - dec_places :]
                formatted = f"{int_part}.{frac_part}"
            else:
                # Integer value — append zeros and decimal places
                int_part = digit_str + "0" * exp
                formatted = f"{int_part}.{'0' * decimals}"
            # Ensure leading zero for 3-arg form (0.xx not .xx)
            if formatted.startswith("."):
                formatted = "0" + formatted
    else:
        # 2-arg form: MUMPS canonical (strip leading/trailing zeros)
        formatted = m_str(abs_value)

    # Step 5: Add comma separators if requested
    if "," in codes_upper:
        parts = formatted.split(".")
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

    # Step 6: Determine sign character based on composable code semantics
    has_p = "P" in codes_upper
    has_t = "T" in codes_upper
    has_plus = "+" in codes_upper
    has_minus = "-" in codes_upper

    if has_p:
        # P mode: parentheses for negative, leading+trailing space for non-negative
        if is_negative:
            return f"({formatted})"
        else:
            return f" {formatted} "

    # Determine what sign character to show
    # - suppress: "-" code suppresses the minus sign
    # - force: "+" code forces + for positive (but NOT zero)
    sign_char = ""
    if is_negative and not has_minus:
        sign_char = "-"
    elif not is_negative and not is_zero and has_plus:
        sign_char = "+"

    if has_t:
        # Trailing sign: sign (or space placeholder) goes after number
        if sign_char:
            return f"{formatted}{sign_char}"
        else:
            return f"{formatted} "
    else:
        # Leading sign (default)
        return f"{sign_char}{formatted}"


# =============================================================================
# $TRANSLATE function
# =============================================================================


def m_translate(string: str, from_chars: str, to_chars: str = "") -> str:
    """Perform MUMPS $TRANSLATE character-by-character replacement.

    Each character in `string` that appears in `from_chars` is replaced by
    the corresponding character in `to_chars`. If `to_chars` is shorter than
    `from_chars`, characters in `from_chars` without a corresponding character
    in `to_chars` are deleted. If `to_chars` is longer than `from_chars`,
    the extra characters in `to_chars` are ignored.

    Args:
        string: The source string to translate
        from_chars: Characters to find in string
        to_chars: Replacement characters (may be shorter, equal, or longer
                  than from_chars)

    Returns:
        Translated string

    Examples:
        >>> m_translate("HELLO", "LO", "XY")
        'HEXXY'
        >>> m_translate("HELLO", "L", "")
        'HEO'
        >>> m_translate("ABCDEFGHIJ", "ABC", "abcdef")
        'abcDEFGHIJ'
    """
    result = []
    for ch in string:
        idx = from_chars.find(ch)
        if idx == -1:
            # Character not in from_chars, keep as is
            result.append(ch)
        elif idx < len(to_chars):
            # Has corresponding replacement character
            result.append(to_chars[idx])
        # else: no corresponding to_char, delete the character
    return "".join(result)


# =============================================================================
# String Comparison Operators
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
# Pattern Match Operator
# =============================================================================


def m_pattern_match(string: Any, pattern: str) -> int:
    """Match string against MUMPS pattern (MUMPS ? operator).

    This runtime helper is used only for indirect patterns (X?@Y) where
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
# NEW Command Scope Management
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
        # Stack-based restore actions for proper NEW unwinding
        # Each entry is ('var', name, value) or ('scope', snapshot_dict)
        self._restore_actions: list = []
        # Track individually NEWed variables for dedup (reset on new_all/new_exclusive)
        self._individually_newed: set = set()

    def __enter__(self) -> "NewScopeManager":
        """Enter the context - nothing to do on entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context - restore all saved variables.

        This runs on both normal return and exceptions, ensuring
        MUMPS NEW semantics are preserved.

        Process restore actions in reverse order to properly
        unwind nested NEW scopes (argumentless/exclusive NEW within
        functions that have formal param NEWs).
        """
        # Process restore actions in reverse (LIFO) for correct unwinding
        for action in reversed(self._restore_actions):
            if action[0] == "scope":
                # Argumentless or exclusive NEW: restore full scope snapshot
                snapshot = action[1]
                self._scope.clear()
                self._scope.update(snapshot)
            else:
                # Individual variable restore
                _, var_name, saved_value = action
                if saved_value is _UNDEFINED:
                    self._scope.pop(var_name, None)
                else:
                    self._scope[var_name] = saved_value

        # Also restore special variables from legacy _saved dict
        for var_name, saved_value in self._saved.items():
            if var_name.startswith("__special__"):
                value, setter = saved_value
                setter(value)

    def new_var(self, var_name: str) -> None:
        """NEW a single variable - save and remove from scope.

        If the variable has already been individually NEWed at the current
        scope level, this is a no-op (first NEW wins per MUMPS spec).

        Uses _individually_newed set for dedup tracking, and
        appends to _restore_actions list for proper stack-based unwinding.

        Args:
            var_name: The translated Python variable name (as stored in _scope)
        """
        if var_name in self._individually_newed:
            # Already NEWed at this scope level - skip
            return
        self._individually_newed.add(var_name)

        # Save current value (or mark as undefined)
        if var_name in self._scope:
            saved_value = self._scope[var_name]
            del self._scope[var_name]
        else:
            saved_value = _UNDEFINED

        self._restore_actions.append(("var", var_name, saved_value))

    def new_all(self) -> None:
        """NEW all local variables - save scope snapshot and clear.

        Argumentless NEW saves the entire scope and clears it.
        Resets the individually-NEWed tracking set so subsequent selective
        NEWs can save variables relative to the new (empty) scope.

        MUMPS semantics: N (without args) makes all local variables
        undefined until restoration at function exit.
        """
        snapshot = dict(self._scope)
        self._scope.clear()
        self._individually_newed.clear()  # Reset for new scope level
        self._restore_actions.append(("scope", snapshot))

    def new_exclusive(self, keep_vars: set) -> None:
        """Exclusive NEW - save all except specified variables.

        Exclusive NEW (N (X,Y)) saves the entire scope snapshot and removes
        all variables NOT in keep_vars. Resets individually-NEWed tracking.

        Args:
            keep_vars: Set of variable names to keep (not NEW'd)
        """
        snapshot = dict(self._scope)
        for k in list(self._scope.keys()):
            if k not in keep_vars:
                del self._scope[k]
        self._individually_newed.clear()  # Reset for new scope level
        self._restore_actions.append(("scope", snapshot))

    def new_special_var(
        self, name: str, current_value: str, setter: "Callable[[str], None]"
    ) -> None:
        """NEW a special variable like $ETRAP or $ECODE.

        Handles NEW for special variables that use
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


def unwind_new_stack(state) -> None:
    """Unwind all NEW frames in state._new_stack on subroutine exit.

    When a subroutine (TRAMPOLINE wrapper) exits via QUIT,
    all NEW frames pushed during that subroutine must be unwound.
    Processes entries in LIFO order (most recent NEW first).

    Entry formats:
        ('all', saved_dict) - Argumentless NEW: restore full snapshot
        ('excl', keep_vars_set, saved_dict) - Exclusive NEW: restore non-kept vars
        ('var', name, saved_value) - Selective NEW: restore single variable
        plain dict - Legacy: treat as argumentless NEW (full snapshot)
    """
    while state._new_stack:
        entry = state._new_stack.pop()
        if isinstance(entry, dict):
            # Legacy format: argumentless NEW (full snapshot)
            state._locals.clear()
            state._locals.update(entry)
        elif entry[0] == "all":
            state._locals.clear()
            state._locals.update(entry[1])
        elif entry[0] == "excl":
            keep_vars = entry[1]
            saved = entry[2]
            # Keep current values of kept variables
            current_kept = {k: v for k, v in state._locals.items() if k in keep_vars}
            state._locals.clear()
            state._locals.update(saved)
            state._locals.update(current_kept)
        elif entry[0] == "var":
            name, saved_value = entry[1], entry[2]
            if saved_value is not None:
                state._locals[name] = saved_value
            else:
                state._locals.pop(name, None)


# =============================================================================
# $ZDATE Function Helper
# =============================================================================

# Default month names (uppercase, 3 chars) used when months arg is empty
_ZDATE_DEFAULT_MONTHS = [
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
]

# Default day names (uppercase, 3 chars) used when days arg is empty
_ZDATE_DEFAULT_DAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]


def m_zdate(
    horolog: str | int, fmt: str = "MM/DD/YY", months: str = "", days: str = ""
) -> str:
    """Format a $HOROLOG value into a human-readable date/time string.

    Implements YDB's $ZDATE format codes (not IRIS numeric codes).

    Args:
        horolog: $HOROLOG string — either "days" or "days,seconds"
        fmt: Format string using YDB codes (MM, DD, YY, YYYY, YEAR, MON, DAY,
             24, 12, 60, SS, AM). Max 64 characters.
        months: Optional comma-separated list of 12 month names
        days: Optional comma-separated list of 7 day-of-week names

    Returns:
        Formatted date/time string

    Examples:
        m_zdate("66337") → "08/16/22"
        m_zdate("66337", "YYYY-MM-DD") → "2022-08-16"
        m_zdate("66337", "DD MON YEAR") → "16 AUG 2022"
        m_zdate("66337,45296", "YYYY-MM-DD 24:60:SS") → "2022-08-16 12:34:56"
    """
    import datetime
    import re

    # Enforce 64-character format string limit per YDB specification
    if len(fmt) > 64:
        from m2py.runtime.exceptions import MRuntimeError

        raise MRuntimeError(
            "ZDATEFMT", f"$ZDATE format string exceeds 64 characters (got {len(fmt)})"
        )

    # Parse $HOROLOG string into days and optional seconds
    horolog_str = str(horolog)
    if "," in horolog_str:
        parts = horolog_str.split(",", 1)
        try:
            day_num = int(parts[0])
        except ValueError:
            day_num = 0
        try:
            seconds = int(parts[1])
        except ValueError:
            seconds = 0
    else:
        try:
            day_num = int(horolog_str)
        except ValueError:
            day_num = 0
        seconds = 0

    # $HOROLOG epoch is December 31, 1840
    epoch = datetime.date(1840, 12, 31)
    try:
        dt = epoch + datetime.timedelta(days=day_num)
    except (OverflowError, ValueError):
        dt = epoch

    # Parse custom month names if provided
    if months:
        month_list = months.split(",")
    else:
        month_list = _ZDATE_DEFAULT_MONTHS

    # Parse custom day names if provided
    if days:
        day_list = days.split(",")
    else:
        day_list = _ZDATE_DEFAULT_DAYS

    # Calculate time components from seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    # 12-hour format calculations
    hour_12 = hours % 12
    if hour_12 == 0:
        hour_12 = 12
    am_pm = "AM" if hours < 12 else "PM"

    # Get month name
    month_idx = dt.month - 1
    if 0 <= month_idx < len(month_list):
        month_name = month_list[month_idx]
    else:
        month_name = _ZDATE_DEFAULT_MONTHS[month_idx]

    # Get day of week name
    # Python weekday: Monday=0..Sunday=6; $H weekday: Sunday=0..Saturday=6
    weekday_python = dt.weekday()  # Monday=0
    weekday_mumps = (weekday_python + 1) % 7  # Convert to Sunday=0
    if 0 <= weekday_mumps < len(day_list):
        day_name = day_list[weekday_mumps]
    else:
        day_name = _ZDATE_DEFAULT_DAYS[weekday_mumps]

    # Build format code to value mapping
    # Order matters for regex - longer patterns must come first
    codes = {
        "YEAR": str(dt.year),
        "YYYY": str(dt.year),
        "MON": month_name,
        "DAY": day_name,
        "YY": f"{dt.year % 100:02d}",
        "MM": f"{dt.month:02d}",
        "DD": f"{dt.day:02d}",
        "SS": f"{secs:02d}",
        "AM": am_pm,
        "60": f"{minutes:02d}",
        "24": f"{hours:02d}",
        "12": f"{hour_12:02d}",
    }

    # Build regex pattern matching all format codes
    # Order: longest first to avoid partial matches (e.g., YYYY before YY)
    pattern = "|".join(re.escape(code) for code in codes.keys())

    # Replace all format codes in one pass using regex
    def replace_code(match: re.Match) -> str:
        return codes[match.group(0)]

    result = re.sub(pattern, replace_code, fmt)

    return result


# =============================================================================
# $ZMESSAGE function — error code to message text
# =============================================================================

# Common YDB error codes and their message text
_YDB_ERROR_MESSAGES: dict[int, str] = {
    150372370: "BADCHAR",
    150372826: "DIVZERO",
    150373066: "FORRANGE",
    150373138: "GVUNDEF",
    150373554: "INVFCN",
    150373706: "LABELUNKNOWN",
    150373770: "SVNOSET",
    150373850: "LVUNDEF",
    150373890: "MAXNRSUBSCRIPTS",
    150373994: "NULSUBSC",
    150374090: "ORDER2",
    150374218: "PATNOTFOUND",
    150374562: "SELECTFALSE",
    150375058: "UNDEF",
    150375298: "RDFLTOOSHORT",
    150375538: "SYNTAXERR",
    150375618: "VAREXPECTED",
    150376642: "ILLEGAL",
    150377506: "EXPR",
    150378082: "INVSVN",
    150378642: "MAXSTRLEN",
    150381058: "NUMOFLOW",
    150382066: "ZDATEBADTIME",
}


def m_zmessage(code: int | str) -> str:
    """Return error message text for a YDB error code.

    Lookup table of common YDB error codes.

    Args:
        code: YDB error code (integer or numeric string)

    Returns:
        Human-readable error message string, or the code as string if unknown
    """
    try:
        code_int = int(code)
    except (ValueError, TypeError):
        return str(code)

    msg = _YDB_ERROR_MESSAGES.get(code_int)
    if msg:
        return f"%YDB-E-{msg}"
    return str(code_int)


# =============================================================================
# IRIS/Caché Vendor Functions (024-vista-transpilation-fixes, US4)
# =============================================================================


def m_replace(
    string: str,
    search: str,
    replace: str,
    start: int = 1,
    count: int = -1,
    case: int = 0,
) -> str:
    """IRIS $REPLACE implementation.

    Replace occurrences of *search* in *string* with *replace*.

    Args:
        string: Source string.
        search: Substring to find. Empty string → return *string* unchanged.
        replace: Replacement text.
        start: 1-based start position. Characters before *start* are **dropped**
               from the result (IRIS semantics).
        count: Max replacements (−1 = all).
        case: 0 = case-sensitive, 1 = case-insensitive.

    Returns:
        Modified string (from *start* onward).
    """
    string = str(string)
    search = str(search)
    replace = str(replace)

    if not search:
        # Empty search → return string from start position
        return string[max(0, start - 1) :]

    # Slice from start (1-based)
    if start > 1:
        string = string[start - 1 :]

    if case == 1:
        # Case-insensitive replacement
        result: list[str] = []
        s_lower = string.lower()
        search_lower = search.lower()
        search_len = len(search)
        idx = 0
        replacements = 0
        while idx <= len(string) - search_len:
            if s_lower[idx : idx + search_len] == search_lower:
                result.append(replace)
                idx += search_len
                replacements += 1
                if count >= 0 and replacements >= count:
                    result.append(string[idx:])
                    return "".join(result)
            else:
                result.append(string[idx])
                idx += 1
        result.append(string[idx:])
        return "".join(result)
    else:
        # Case-sensitive
        if count < 0:
            return string.replace(search, replace)
        return string.replace(search, replace, count)


def m_zboolean(arg1: Any, arg2: Any, op: int) -> Any:
    """IRIS $ZBOOLEAN — 16-operation bitwise Boolean.

    When both args are numeric → integer bitwise operations.
    When either arg is non-numeric string → per-character byte operations.

    Args:
        arg1: First operand.
        arg2: Second operand.
        op: Operation code 0–15.

    Returns:
        Integer or string result depending on operand types.
    """
    op = int(op)
    if op < 0 or op > 15:
        raise ValueError(f"$ZBOOLEAN operation code must be 0-15, got {op}")

    # Determine mode: string if either arg is non-numeric string
    a1_str = str(arg1)
    a2_str = str(arg2)
    a1_int = 0
    a2_int = 0
    is_string_mode = False
    try:
        a1_int = int(Decimal(a1_str))
        a2_int = int(Decimal(a2_str))
    except Exception:
        is_string_mode = True

    if is_string_mode:
        return _zboolean_string(a1_str, a2_str, op)
    else:
        return _zboolean_int(a1_int, a2_int, op)


def _zboolean_int(a: int, b: int, op: int) -> int:
    """Integer-mode $ZBOOLEAN dispatch."""
    # fmt: off
    ops = {
        0:  lambda a, b: 0,           # FALSE
        1:  lambda a, b: a & b,       # AND
        2:  lambda a, b: a & ~b,      # arg1 AND NOT arg2
        3:  lambda a, b: a,           # arg1
        4:  lambda a, b: ~a & b,      # NOT arg1 AND arg2
        5:  lambda a, b: b,           # arg2
        6:  lambda a, b: a ^ b,       # XOR
        7:  lambda a, b: a | b,       # OR
        8:  lambda a, b: ~(a | b),    # NOR
        9:  lambda a, b: ~(a ^ b),    # XNOR
        10: lambda a, b: ~b,          # NOT arg2
        11: lambda a, b: a | ~b,      # arg1 OR NOT arg2
        12: lambda a, b: ~a,          # NOT arg1
        13: lambda a, b: ~a | b,      # NOT arg1 OR arg2
        14: lambda a, b: ~(a & b),    # NAND
        15: lambda a, b: -1,          # TRUE (all bits set)
    }
    # fmt: on
    return ops[op](a, b)


def _zboolean_string(a: str, b: str, op: int) -> str:
    """String-mode $ZBOOLEAN — per-byte bitwise operations.

    The shorter string is cycled (repeated) to match the length of the longer
    string. This matches IRIS behavior where $ZBOOLEAN("abcd","_",1) = "ABCD"
    because "_" (0x5F) is repeated to "____" and AND with "abcd" gives "ABCD".
    """
    max_len = max(len(a), len(b))
    if not a:
        a = "\x00"
    if not b:
        b = "\x00"
    # Cycle shorter string to match length of longer
    a_bytes = (a * (max_len // len(a) + 1))[:max_len]
    b_bytes = (b * (max_len // len(b) + 1))[:max_len]

    result_chars = []
    for ca, cb in zip(a_bytes, b_bytes):
        byte_result = _zboolean_int(ord(ca), ord(cb), op) & 0xFF
        result_chars.append(chr(byte_result))
    return "".join(result_chars)


def m_zu(code: int | str, *args: Any) -> Any:
    """IRIS $ZU utility function dispatcher.

    Implements the subset of $ZU codes used by VistA.

    Args:
        code: $ZU function code.
        *args: Additional arguments.

    Returns:
        Result string or integer.
    """
    code_int = int(code)

    if code_int == 0:
        # $ZU(0) → namespace name
        return "VISTA"
    elif code_int == 5:
        # $ZU(5) → namespace; $ZU(5,ns) → set namespace
        if args:
            return "VISTA"  # set is a no-op in transpiler context
        return "VISTA"
    elif code_int == 12:
        # $ZU(12) → config directory
        return os.getcwd()
    elif code_int == 53:
        # $ZU(53) → $IO value
        return "0"
    elif code_int == 56:
        # $ZU(56,2) → collation info
        return 0
    elif code_int == 68:
        # $ZU(68,...) → various config no-ops
        return 0
    elif code_int == 140:
        # $ZU(140,4,file) → file exists check
        if len(args) >= 2:
            return 1 if os.path.exists(str(args[1])) else 0
        return 0
    elif code_int == 168:
        # $ZU(168) → current directory
        return os.getcwd()
    elif code_int == 190:
        # $ZU(190,17) → block collision stub
        return 0
    else:
        # Unknown $ZU code — return empty string with warning
        warnings.warn(f"$ZU({code_int}) not implemented, returning empty string")
        return ""


def m_zf(code: int | str, *args: Any) -> Any:
    """IRIS $ZF external function family.

    Args:
        code: Function variant code or string name.
        *args: Arguments for the specific $ZF variant.

    Returns:
        Integer exit code or string result.
    """
    # Handle string codes (VMS stubs)
    if isinstance(code, str):
        code_str = code.upper()
        if code_str in ("GETSYM", "GETJPI", "TRNLNM"):
            return ""
        # Numeric string
        try:
            code_int = int(code)
        except (ValueError, TypeError):
            return ""
    else:
        code_int = int(code)

    if code_int == -1:
        # $ZF(-1
        if args:
            cmd = str(args[0])
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
            return result.returncode
        return 0
    elif code_int == -2:
        # $ZF(-2, cmd) — launch async
        if args:
            cmd = str(args[0])
            subprocess.Popen(cmd, shell=True)  # noqa: S602
        return 0
    elif code_int == -100:
        # $ZF(-100, flags, cmd, *cmdargs)
        if len(args) >= 2:
            cmd = str(args[1])
            cmd_args = [str(a) for a in args[2:]]
            try:
                result = subprocess.run(
                    [cmd] + cmd_args, capture_output=True, timeout=30
                )
                return result.returncode
            except FileNotFoundError:
                return -1
        return 0
    else:
        return ""


def m_zcall_stub(name: str, *args: Any) -> str:
    """Stub for $& external function calls.

    VistA uses $& (formerly $ZF(name,...)) format for external calls.
    These are C/DLL callouts that cannot run in Python.
    Returns empty string with a warning.
    """
    warnings.warn(f"$&{name} external call not available, returning empty string")
    return ""


def m_view_func_stub(*args: Any) -> str:
    """Stub for $VIEW function.

    $VIEW is implementation-specific and cannot be meaningfully transpiled.
    Returns empty string.
    """
    return ""


def m_zconvert(string: str, mode: str) -> str:
    """Implement $ZCONVERT/$ZCVT — string case conversion (IRIS/Caché).

    Args:
        string: Input string
        mode: "U" (upper), "L" (lower), "S" (sentence — capitalize first),
              "W" (word — capitalize each word), "T" (same as "U" in IRIS)

    Returns:
        Converted string. Unknown modes return the original string.
    """
    mode_upper = mode.upper()
    if mode_upper in ("U", "T"):
        return string.upper()
    elif mode_upper == "L":
        return string.lower()
    elif mode_upper == "S":
        # Sentence case: capitalize first character only
        return string[:1].upper() + string[1:] if string else string
    elif mode_upper == "W":
        # Word case: capitalize first letter of each word
        return string.title()
    return string


# =============================================================================
# Phase 10: Vendor Runtime Helpers (024-vista-transpilation-fixes)
# =============================================================================


def _rt_os_environ_get(name: str) -> str:
    """Get environment variable value, returning "" if not set.

    Used by $ZTRNLNM (VMS/YDB translate logical name).
    """
    import os

    return os.environ.get(name, "")


def _rt_os_getcwd() -> str:
    """Get current working directory.

    Used by $ZDIR (GT.M/YDB current directory function).
    """
    import os

    return os.getcwd()


def m_zgetjpi(pid: str, item: str) -> str:
    """Implement $ZGETJPI — get job/process information (YDB).

    Common usage: $ZGETJPI(pid, "ISPROCALIVE") — returns "1" if process is alive.

    Args:
        pid: Process ID ("" for current process)
        item: Info item name (e.g., "ISPROCALIVE")

    Returns:
        String result
    """
    import os
    import signal

    item_upper = item.upper()

    if item_upper == "ISPROCALIVE":
        if pid == "" or pid == "0":
            return "1"  # Current process is always alive
        try:
            os.kill(int(pid), signal.SIG_DFL)
            return "1"
        except (ProcessLookupError, ValueError):
            return "0"
        except PermissionError:
            return "1"  # Process exists but we can't signal it

    # For unknown items, return empty string
    warnings.warn(f"$ZGETJPI item {item!r} not implemented, returning empty string")
    return ""


def m_zparse(path: str, item: str = "") -> str:
    """Implement $ZPARSE — file path parsing (YDB/GT.M).

    $ZPARSE(path[,item]) parses file paths.
    item can be: "DIRECTORY", "NAME", "TYPE", "NODE", "DEVICE"
    If item is empty, returns the full expanded path.

    Args:
        path: File path to parse
        item: Component to extract

    Returns:
        Requested path component as string
    """
    import os

    item_upper = item.upper()

    if not item or item_upper == "FULL":
        return os.path.abspath(path) if path else ""

    if item_upper == "DIRECTORY":
        return os.path.dirname(path)
    elif item_upper == "NAME":
        base = os.path.basename(path)
        name, _ = os.path.splitext(base)
        return name
    elif item_upper in ("TYPE", "EXTENSION"):
        base = os.path.basename(path)
        _, ext = os.path.splitext(base)
        return ext
    elif item_upper in ("NODE", "DEVICE"):
        return ""  # No network/device on Unix

    return path


def m_zbitand(s1: str, s2: str) -> str:
    """Implement $ZBITAND — bitwise AND on byte strings.

    Performs byte-by-byte AND on two strings. Result length = min of both.

    Args:
        s1: First byte string
        s2: Second byte string

    Returns:
        Result of bitwise AND
    """
    b1 = s1.encode("latin-1") if s1 else b""
    b2 = s2.encode("latin-1") if s2 else b""
    min_len = min(len(b1), len(b2))
    result = bytes(b1[i] & b2[i] for i in range(min_len))
    return result.decode("latin-1")


def m_zbitor(s1: str, s2: str) -> str:
    """Implement $ZBITOR — bitwise OR on byte strings.

    Performs byte-by-byte OR on two strings. Result length = max of both.
    Shorter string is right-padded with NUL bytes.

    In YDB, $ZBITOR operates on GT.M bit strings (header + data bytes).
    This implementation handles both raw byte strings and GT.M bit strings
    by doing byte-by-byte OR with zero-padding.

    Args:
        s1: First byte string
        s2: Second byte string

    Returns:
        Result of bitwise OR
    """
    b1 = s1.encode("latin-1") if s1 else b""
    b2 = s2.encode("latin-1") if s2 else b""
    max_len = max(len(b1), len(b2))
    # Pad shorter string with NUL bytes
    b1 = b1.ljust(max_len, b"\x00")
    b2 = b2.ljust(max_len, b"\x00")
    result = bytes(b1[i] | b2[i] for i in range(max_len))
    return result.decode("latin-1")


def m_zbitxor(s1: str, s2: str) -> str:
    """Implement $ZBITXOR — bitwise XOR on byte strings.

    Performs byte-by-byte XOR on two strings. Result length = max of both.
    Shorter string is right-padded with NUL bytes.

    Args:
        s1: First byte string
        s2: Second byte string

    Returns:
        Result of bitwise XOR
    """
    b1 = s1.encode("latin-1") if s1 else b""
    b2 = s2.encode("latin-1") if s2 else b""
    max_len = max(len(b1), len(b2))
    b1 = b1.ljust(max_len, b"\x00")
    b2 = b2.ljust(max_len, b"\x00")
    result = bytes(b1[i] ^ b2[i] for i in range(max_len))
    return result.decode("latin-1")


def m_zbitnot(s1: str) -> str:
    """Implement $ZBITNOT — bitwise NOT on byte strings.

    Performs byte-by-byte NOT (complement) on a string.

    Args:
        s1: Byte string

    Returns:
        Result of bitwise NOT
    """
    b1 = s1.encode("latin-1") if s1 else b""
    result = bytes(~b & 0xFF for b in b1)
    return result.decode("latin-1")


def m_zbitstr(length: str, value: str = "0") -> str:
    """Implement $ZBITSTR — create a bitstring of n bits.

    Creates a YDB-format bitstring: 1-byte header + data bytes.
    Header byte = number of unused bits in the last data byte.
    Data bytes are initialized to all 0s (value=0) or all 1s (value=1).

    Format:
        byte 0: (8 - (n % 8)) % 8  (unused trailing bits)
        bytes 1..ceil(n/8): data bytes

    Examples:
        $ZBITSTR(8,0) → [0x00, 0x00]  (header=0, 1 zero byte)
        $ZBITSTR(8,1) → [0x00, 0xFF]  (header=0, 1 all-ones byte)
        $ZBITSTR(4,0) → [0x04, 0x00]  (header=4, 4 unused bits)
        $ZBITSTR(16,0) → [0x00, 0x00, 0x00]  (header=0, 2 zero bytes)

    Args:
        length: Number of bits (coerced to non-negative integer)
        value: "0" (default) or "1" to initialize all bits

    Returns:
        Bitstring as a latin-1 encoded string
    """
    import math

    from m2py.core.values import m_num

    n = int(m_num(length))
    v = int(m_num(value))
    if n <= 0:
        # Zero or negative length: just a header byte with 0 unused bits
        return "\x00"
    num_data_bytes = math.ceil(n / 8)
    unused_bits = (8 - (n % 8)) % 8
    header = bytes([unused_bits])
    if v:
        data = bytes([0xFF] * num_data_bytes)
    else:
        data = bytes([0x00] * num_data_bytes)
    return (header + data).decode("latin-1")


def m_zabs(value: str) -> str:
    """Implement $ZABS — absolute value.

    IRIS-specific function that returns the absolute value of a numeric expression.
    Non-numeric strings are coerced to 0 via m_num().

    Args:
        value: String representation of the number

    Returns:
        String representation of the absolute value
    """
    from m2py.core.values import m_num, m_str

    n = m_num(value)
    return m_str(abs(n))


def m_now() -> str:
    """Implement $NOW — current timestamp in $HOROLOG format with fractional seconds.

    Returns a string in the format "days,seconds.fraction" where:
    - days = number of days since December 31, 1840
    - seconds = seconds since midnight with microsecond precision

    This is similar to $HOROLOG but with fractional seconds.

    Returns:
        $HOROLOG-format timestamp with fractional seconds
    """
    import datetime

    # MUMPS epoch: December 31, 1840
    mumps_epoch = datetime.date(1840, 12, 31)
    now = datetime.datetime.now()
    today = now.date()

    days = (today - mumps_epoch).days
    # Seconds since midnight with fractional part
    seconds_since_midnight = (
        now.hour * 3600 + now.minute * 60 + now.second + now.microsecond / 1_000_000
    )
    # Format: remove trailing zeros but keep at least one decimal
    sec_str = f"{seconds_since_midnight:.6f}".rstrip("0").rstrip(".")

    return f"{days},{sec_str}"


def m_ztime(seconds: str) -> str:
    """Implement $ZTIME/$ZT — format seconds as HH:MM:SS.

    Converts a number of seconds (like $HOROLOG second part) to
    a time string in HH:MM:SS format.

    Args:
        seconds: String representation of seconds since midnight

    Returns:
        Formatted time string "HH:MM:SS"
    """
    from m2py.core.values import m_num

    total = int(m_num(seconds))
    if total < 0:
        total = 0
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def m_zgetsyi(keyword: str) -> str:
    """Implement $ZGETSYI — system information query.

    Returns system information based on keyword.
    GT.M/YDB specific function.

    Args:
        keyword: Information keyword (e.g., "NODENAME")

    Returns:
        Requested system information, or empty string for unknown keywords
    """
    import platform

    kw = keyword.upper().strip('"')
    if kw == "NODENAME":
        return platform.node()
    return ""
