"""MUMPS value model helper functions for code generation.

These pure functions implement MUMPS semantics for generated Python code:
- m_str(): String coercion (MUMPS-style number formatting)
- m_num(): Numeric coercion (ANSI 7.1.4.5)
- m_truth(): Truth evaluation (ANSI 1.2.4)
- m_compare(): Comparison with appropriate coercion

These are imported into generated code to ensure correct MUMPS behavior.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Union


def m_str(value: Any) -> str:
    """Convert a value to its MUMPS string representation.

    MUMPS always displays numbers in decimal notation (no scientific notation).
    This function ensures Python numbers are formatted the same way MUMPS would
    display them, which is critical for string operations like concatenation
    and the follows (]) operator.

    Args:
        value: Any Python value to convert to string

    Returns:
        MUMPS-style string representation

    Examples:
        >>> m_str(7e-15)
        '.000000000000007'
        >>> m_str(7e15)
        '7000000000000000'
        >>> m_str(3.14)
        '3.14'
        >>> m_str(3)
        '3'
        >>> m_str("hello")
        'hello'
        >>> m_str(0)
        '0'
        >>> from decimal import Decimal
        >>> m_str(Decimal("9999997799E14"))
        '999999779900000000000000'
    """
    # Handle Decimal type directly for precise large numbers
    if isinstance(value, Decimal):
        d = value
    elif isinstance(value, int):
        # Integer values: simple string conversion
        return str(value)
    elif isinstance(value, float):
        # Float values: convert to Decimal for precise formatting
        if value == 0.0:
            return "0"
        d = Decimal(str(value))
    else:
        # Non-numeric values: use Python's str()
        return str(value)

    # Convert Decimal to MUMPS-style fixed-point string (no scientific notation)
    sign, digits, exponent = d.as_tuple()

    # Handle special Decimal values (NaN, Infinity) - exponent is a string code
    if not isinstance(exponent, int):
        return str(d)

    if exponent >= 0:
        # Integer or large number
        result = "".join(str(dig) for dig in digits) + "0" * exponent
        if sign:
            result = "-" + result
    else:
        # Decimal number
        digits_str = "".join(str(dig) for dig in digits)
        exp = -exponent  # Convert to positive

        if exp >= len(digits_str):
            # Need leading zeros after decimal point: 0.00007
            result = "." + "0" * (exp - len(digits_str)) + digits_str
        else:
            # Decimal point within digits: 3.14
            pos = len(digits_str) - exp
            result = digits_str[:pos] + "." + digits_str[pos:]

        # Strip trailing zeros after decimal point
        if "." in result:
            result = result.rstrip("0").rstrip(".")

        if sign:
            result = "-" + result

    # MUMPS canonicalizes: no leading zeros except for 0.xxx
    # Strip leading zeros but keep "0" for values like 0.5
    if result.startswith("0") and len(result) > 1 and result[1] != ".":
        result = result.lstrip("0") or "0"
    if result.startswith("-0") and len(result) > 2 and result[2] != ".":
        result = "-" + result[2:].lstrip("0")

    return result


def m_num(value: Any) -> Union[int, float, Decimal]:
    """Convert a value to its MUMPS numeric interpretation.

    Implements ANSI MUMPS 7.1.4.5 numeric coercion rules:
    1. If already numeric, return as-is
    2. For strings:
       - Parse left-to-right from position 0
       - Process leading signs (++→+, +-→-, -+→-, --→+)
       - Extract longest left-head matching numeric literal
       - Return 0 if first char is non-numeric/non-sign (including whitespace!)
       - Return canonicalized number

    NOTE: Leading whitespace makes a string non-numeric! " 42" → 0

    Args:
        value: Any Python value to convert

    Returns:
        Integer, float, or Decimal numeric interpretation

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
        >>> m_num("  42")  # Leading space makes it non-numeric!
        0
        >>> m_num("+-5")
        -5
        >>> m_num("--5")
        5
        >>> m_num("3.14ABC")
        3.14
    """
    # Decimal values - keep as Decimal for precision (large numbers)
    if isinstance(value, Decimal):
        # Normalize: if it's an integer value, return int
        # But only if it fits in int range without precision loss
        if value == int(value):
            return int(value)
        return value

    # Already numeric - normalize float to int if it's a whole number
    if isinstance(value, float):
        if value == int(value):
            return int(value)
        return value
    if isinstance(value, int):
        return value

    # Convert to string for processing
    s = str(value)

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

    # Find longest numeric prefix including optional exponential notation
    # Pattern: optional digits, optional decimal point, optional more digits,
    # optional exponent (E/e followed by optional sign and digits)
    match = re.match(r"(\d*\.?\d*)([Ee][+-]?\d+)?", s)
    if not match:
        return 0

    num_str = match.group(1)
    exp_str = match.group(2) or ""

    # Empty numeric part or just decimal point → 0
    if not num_str or num_str == ".":
        return 0

    # Combine mantissa and exponent
    full_num_str = num_str + exp_str

    # Parse and apply sign
    try:
        if "." in num_str or exp_str:
            # Use Decimal for precise handling of exponential notation
            result = Decimal(full_num_str) * sign
            # Normalize: if it's an integer value, return int
            if result == int(result):
                return int(result)
            # For small floats, convert to float for normal handling
            if abs(result) < Decimal("1e15") and abs(result) > Decimal("1e-15"):
                return float(result)
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


def m_compare(left: Any, op: str, right: Any) -> int:
    """Perform MUMPS comparison with appropriate coercion.

    MUMPS comparison rules:
    - "=": Canonical string equality - numeric values are normalized first
    - "<", ">": Numeric comparison (both operands coerced via m_num)

    For "=" operator, MUMPS normalizes numeric values to their canonical
    string form before comparison. For example:
    - 3.0 = 3 → 1 (both normalize to "3")
    - "3.0" = 3 → 0 (string "3.0" vs canonical "3")

    Args:
        left: Left operand
        op: Comparison operator ("=", "<", ">")
        right: Right operand

    Returns:
        1 if comparison is true, 0 if false (MUMPS integers, not Python bool)

    Examples:
        >>> m_compare("3", "=", "3")
        1
        >>> m_compare("3", "=", 3)
        1  # string "3" = canonical "3"
        >>> m_compare(3, "=", 3)
        1
        >>> m_compare(3.0, "=", 3)
        1  # 3.0 normalizes to 3
        >>> m_compare("3.0", "=", 3)
        0  # string "3.0" ≠ canonical "3"
        >>> m_compare("3A", "<", 5)
        1  # 3 < 5
        >>> m_compare("", "<", 1)
        1  # 0 < 1
    """
    if op == "=":
        # MUMPS "=" compares canonical string representations
        # Numeric values (int, float) are normalized first via m_num
        # Strings remain as-is (they're already the canonical form)
        if isinstance(left, (int, float)):
            left = str(m_num(left))
        else:
            left = str(left)
        if isinstance(right, (int, float)):
            right = str(m_num(right))
        else:
            right = str(right)
        return int(left == right)
    elif op == "<":
        return int(m_num(left) < m_num(right))
    elif op == ">":
        return int(m_num(left) > m_num(right))
    else:
        raise ValueError(f"Unsupported comparison operator: {op}")


__all__ = ["m_str", "m_num", "m_truth", "m_compare"]
