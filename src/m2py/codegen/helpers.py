"""MUMPS value model helper functions for code generation.

These pure functions implement MUMPS semantics for generated Python code:
- m_num(): Numeric coercion (ANSI 7.1.4.5)
- m_truth(): Truth evaluation (ANSI 1.2.4)
- m_compare(): Comparison with appropriate coercion

These are imported into generated code to ensure correct MUMPS behavior.
"""

from __future__ import annotations

import re
from typing import Any, Union


def m_num(value: Any) -> Union[int, float]:
    """Convert a value to its MUMPS numeric interpretation.

    Implements ANSI MUMPS 7.1.4.5 numeric coercion rules:
    1. If already numeric, return as-is
    2. For strings:
       - Strip leading whitespace
       - Process leading signs (++→+, +-→-, -+→-, --→+)
       - Extract longest left-head matching numeric literal
       - Return 0 if no numeric prefix
       - Return canonicalized number

    Args:
        value: Any Python value to convert

    Returns:
        Integer or float numeric interpretation

    Examples:
        >>> m_num(3)
        3
        >>> m_num("3")
        3
        >>> m_num("3A")
        3
        >>> m_num("A3")
        0
        >>> m_num("")
        0
        >>> m_num("007")
        7
        >>> m_num("  42")
        42
        >>> m_num("+-5")
        -5
        >>> m_num("--5")
        5
        >>> m_num("3.14ABC")
        3.14
    """
    # Already numeric - return as-is
    if isinstance(value, (int, float)):
        return value

    # Convert to string for processing
    s = str(value)

    # Strip leading whitespace
    s = s.lstrip()

    # Empty string → 0
    if not s:
        return 0

    # Process leading signs and reduce them
    sign = 1
    while s and s[0] in "+-":
        if s[0] == "-":
            sign = -sign
        s = s[1:]

    # Empty after sign processing → 0
    if not s:
        return 0

    # Find longest numeric prefix (digits and at most one decimal point)
    # Pattern: optional digits, optional decimal point, optional more digits
    match = re.match(r"(\d*\.?\d*)", s)
    if not match:
        return 0

    num_str = match.group(1)

    # Empty numeric part or just decimal point → 0
    if not num_str or num_str == ".":
        return 0

    # Parse and apply sign
    try:
        if "." in num_str:
            result = float(num_str) * sign
            # Normalize: if it's an integer value, return int
            if result == int(result):
                return int(result)
            return result
        else:
            return int(num_str) * sign
    except ValueError:
        return 0


def m_truth(value: Any) -> bool:
    """Evaluate MUMPS truth value.

    Implements ANSI MUMPS 1.2.4:
    A value is true if and only if its numeric interpretation is nonzero.

    Args:
        value: Any Python value to evaluate

    Returns:
        True if m_num(value) != 0, False otherwise

    Examples:
        >>> m_truth(1)
        True
        >>> m_truth(0)
        False
        >>> m_truth("")
        False
        >>> m_truth("0")
        False
        >>> m_truth("1")
        True
        >>> m_truth("1A")
        True
        >>> m_truth("A")
        False
        >>> m_truth("A1")
        False
    """
    return m_num(value) != 0


def m_compare(left: Any, op: str, right: Any) -> bool:
    """Perform MUMPS comparison with appropriate coercion.

    MUMPS comparison rules:
    - "=": String equality (exact match, no coercion)
    - "<", ">": Numeric comparison (both operands coerced via m_num)

    Args:
        left: Left operand
        op: Comparison operator ("=", "<", ">")
        right: Right operand

    Returns:
        Boolean comparison result

    Examples:
        >>> m_compare("3", "=", "3")
        True
        >>> m_compare("3", "=", 3)
        False  # string "3" ≠ int 3
        >>> m_compare(3, "=", 3)
        True
        >>> m_compare("3A", "<", 5)
        True  # 3 < 5
        >>> m_compare("", "<", 1)
        True  # 0 < 1
    """
    if op == "=":
        # String equality - convert both to string for comparison
        return str(left) == str(right)
    elif op == "<":
        return m_num(left) < m_num(right)
    elif op == ">":
        return m_num(left) > m_num(right)
    else:
        raise ValueError(f"Unsupported comparison operator: {op}")


__all__ = ["m_num", "m_truth", "m_compare"]
