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
        # Handle negative zero - MUMPS doesn't distinguish -0 from 0
        if d == 0:
            return "0"
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
            # If we stripped everything (e.g., ".000000" -> ""), use "0"
            if not result:
                result = "0"

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
    # optional exponent (E followed by optional sign and digits)
    # MUMPS SPEC: Only uppercase E is recognized for scientific notation!
    # "123e2" → 123, "123E2" → 12300
    match = re.match(r"(\d*\.?\d*)(E[+-]?\d+)?", s)
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
            # Use Decimal for precise handling - preserves exact precision
            # and avoids scientific notation on output (m_format_output handles Decimal)
            result = Decimal(full_num_str) * sign
            # Normalize: if it's an integer value, return int
            if result == int(result):
                return int(result)
            # Keep as Decimal to preserve precision and formatting
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


def m_div(left: Any, right: Any) -> Decimal:
    """Perform MUMPS division with 18-digit precision.

    MUMPS uses 18 significant digits for arithmetic operations.
    Python float only provides ~15-16 digits. To match MUMPS/YDB precision,
    we use Decimal with precision 18 for division.

    Args:
        left: Dividend (any value, will be coerced via m_num)
        right: Divisor (any value, will be coerced via m_num)

    Returns:
        Decimal result with 18 significant digits

    Examples:
        >>> m_div(4, 3)
        Decimal('1.33333333333333333')
        >>> m_div("10", "3")
        Decimal('3.33333333333333333')
    """
    from decimal import localcontext

    # Coerce operands to numeric
    left_num = m_num(left)
    right_num = m_num(right)

    # Use Decimal for precise 18-digit division (MUMPS precision)
    with localcontext() as ctx:
        ctx.prec = 18
        left_dec = (
            Decimal(str(left_num)) if not isinstance(left_num, Decimal) else left_num
        )
        right_dec = (
            Decimal(str(right_num)) if not isinstance(right_num, Decimal) else right_num
        )
        return left_dec / right_dec


def m_add(left: Any, right: Any) -> Union[int, Decimal]:
    """Perform MUMPS addition with 18-digit precision.

    MUMPS uses 18 significant digits for arithmetic operations.
    Using Decimal prevents floating point accumulation errors.

    Args:
        left: First operand (any value, will be coerced via m_num)
        right: Second operand (any value, will be coerced via m_num)

    Returns:
        Integer if result is whole number, otherwise Decimal

    Examples:
        >>> m_add(1, 2)
        3
        >>> m_add(0.001, 0.001)
        Decimal('0.002')
    """
    from decimal import localcontext

    left_num = m_num(left)
    right_num = m_num(right)

    with localcontext() as ctx:
        ctx.prec = 18
        left_dec = (
            Decimal(str(left_num)) if not isinstance(left_num, Decimal) else left_num
        )
        right_dec = (
            Decimal(str(right_num)) if not isinstance(right_num, Decimal) else right_num
        )
        result = left_dec + right_dec
        # Normalize: return int for whole numbers
        if result == int(result):
            return int(result)
        return result


def m_sub(left: Any, right: Any) -> Union[int, Decimal]:
    """Perform MUMPS subtraction with 18-digit precision.

    MUMPS uses 18 significant digits for arithmetic operations.
    Using Decimal prevents floating point accumulation errors.

    Args:
        left: First operand (any value, will be coerced via m_num)
        right: Second operand (any value, will be coerced via m_num)

    Returns:
        Integer if result is whole number, otherwise Decimal

    Examples:
        >>> m_sub(3, 2)
        1
        >>> m_sub(0.003, 0.001)
        Decimal('0.002')
    """
    from decimal import localcontext

    left_num = m_num(left)
    right_num = m_num(right)

    with localcontext() as ctx:
        ctx.prec = 18
        left_dec = (
            Decimal(str(left_num)) if not isinstance(left_num, Decimal) else left_num
        )
        right_dec = (
            Decimal(str(right_num)) if not isinstance(right_num, Decimal) else right_num
        )
        result = left_dec - right_dec
        # Normalize: return int for whole numbers
        if result == int(result):
            return int(result)
        return result


def m_mul(left: Any, right: Any) -> Union[int, Decimal]:
    """Perform MUMPS multiplication with 18-digit precision.

    MUMPS uses 18 significant digits for arithmetic operations.
    Using Decimal prevents floating point precision loss.

    Args:
        left: First operand (any value, will be coerced via m_num)
        right: Second operand (any value, will be coerced via m_num)

    Returns:
        Integer if result is whole number, otherwise Decimal

    Examples:
        >>> m_mul(3, 4)
        12
        >>> m_mul(0.01, 0.02)
        Decimal('0.0002')
    """
    from decimal import localcontext

    left_num = m_num(left)
    right_num = m_num(right)

    with localcontext() as ctx:
        ctx.prec = 18
        left_dec = (
            Decimal(str(left_num)) if not isinstance(left_num, Decimal) else left_num
        )
        right_dec = (
            Decimal(str(right_num)) if not isinstance(right_num, Decimal) else right_num
        )
        result = left_dec * right_dec
        # Normalize: return int for whole numbers
        if result == int(result):
            return int(result)
        return result


def m_mod(left: Any, right: Any) -> Union[int, float, Decimal]:
    """Perform MUMPS modulo operation (# operator).

    MUMPS modulo uses floor division semantics:
        result = dividend - (divisor * floor(dividend / divisor))

    This differs from Python's Decimal % which uses truncation towards zero.
    Python's float % operator happens to match MUMPS semantics (floor division).

    Args:
        left: Dividend (will be coerced via m_num)
        right: Divisor (will be coerced via m_num)

    Returns:
        Modulo result - integer if possible, otherwise Decimal

    Examples:
        >>> m_mod(7, 3)
        1
        >>> m_mod(-597.5, 25)
        Decimal('2.5')
        >>> m_mod(-7, 3)
        2
    """
    import math
    from decimal import localcontext

    left_num = m_num(left)
    right_num = m_num(right)

    # Use high precision for Decimal operations
    with localcontext() as ctx:
        ctx.prec = 18

        # Convert both to Decimal for consistent precision
        left_dec = (
            Decimal(str(left_num)) if not isinstance(left_num, Decimal) else left_num
        )
        right_dec = (
            Decimal(str(right_num)) if not isinstance(right_num, Decimal) else right_num
        )

        # MUMPS modulo: dividend - (divisor * floor(dividend / divisor))
        # Note: Decimal's % uses truncation, but MUMPS wants floor division
        quotient = left_dec / right_dec
        # Use math.floor on the float representation for correct floor semantics
        floored = Decimal(str(math.floor(float(quotient))))
        result = left_dec - (right_dec * floored)

        # Normalize: return int for whole numbers
        if result == int(result):
            return int(result)
        return result


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
        # Numeric values (int, float, Decimal) are normalized via m_str
        # Strings remain as-is (they're already the canonical form)
        if isinstance(left, (int, float, Decimal)):
            left = m_str(left)
        else:
            left = str(left)
        if isinstance(right, (int, float, Decimal)):
            right = m_str(right)
        else:
            right = str(right)
        return int(left == right)
    elif op == "<":
        return int(m_num(left) < m_num(right))
    elif op == ">":
        return int(m_num(left) > m_num(right))
    else:
        raise ValueError(f"Unsupported comparison operator: {op}")


def m_range(start: Any, end: Any, step: Any):
    """Generate values from start to end with step (MUMPS FOR semantics).

    Unlike Python's range(), this supports non-integer values for all arguments.
    MUMPS FOR is end-inclusive:
    - F I=1:1:3 iterates I=1,2,3 (not 1,2 like Python range)
    - F I=.001:.01:1 works with fractional steps

    Args:
        start: Starting value (will be coerced via m_num)
        end: Ending value, inclusive (will be coerced via m_num)
        step: Step value (will be coerced via m_num)

    Yields:
        Numeric values from start to end (inclusive) by step

    Examples:
        >>> list(m_range(1, 3, 1))
        [1, 2, 3]
        >>> list(m_range(0, 0.03, 0.01))  # Fractional step
        [0, 0.01, 0.02, 0.03]
        >>> list(m_range(3, 1, -1))  # Negative step
        [3, 2, 1]
    """
    current = m_num(start)
    end_val = m_num(end)
    step_val = m_num(step)

    if step_val > 0:
        while current <= end_val:
            yield current
            current = m_add(current, step_val)
    elif step_val < 0:
        while current >= end_val:
            yield current
            current = m_add(current, step_val)
    # step == 0 would cause infinite loop, yield nothing


__all__ = [
    "m_str",
    "m_num",
    "m_truth",
    "m_compare",
    "m_div",
    "m_add",
    "m_sub",
    "m_mul",
    "m_mod",
    "m_range",
]
