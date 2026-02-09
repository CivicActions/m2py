"""MUMPS value semantics — canonical source of truth.

All MUMPS value-model functions live here.  ``codegen/helpers.py``
re-exports the public symbols for backward compatibility with
generated code.

Constitution VI (Cross-Cutting Semantics): a single implementation
shared by codegen, runtime, and core layers.

Feature: 019-foundation-cleanup
Requirements: FR-011, FR-012, FR-013, FR-014, FR-020
"""

from __future__ import annotations

import re
from decimal import Decimal, localcontext
from typing import Any, Union


# ---------------------------------------------------------------------------
# Canonical number → string  (FR-011)
# ---------------------------------------------------------------------------


def mumps_canonical_str(value: Union[int, float, Decimal]) -> str:
    """Convert a numeric value to its MUMPS canonical string representation.

    Rules (ANSI MUMPS §7.1.4.1):
    - No trailing zeros after the decimal point
    - No unnecessary decimal point for integers
    - No leading zero for ``|value| < 1``  (``0.5`` → ``".5"``)
    - No scientific notation  (``1E+2`` → ``"100"``)
    - Exponent guard: ``exponent < -43`` → ``"0"``  (YDB behaviour)

    Args:
        value: A numeric value (int, float, or Decimal).

    Returns:
        MUMPS canonical string representation.

    Examples:
        >>> mumps_canonical_str(7e-15)
        '.000000000000007'
        >>> mumps_canonical_str(7e15)
        '7000000000000000'
        >>> mumps_canonical_str(Decimal("1E-44"))
        '0'
        >>> mumps_canonical_str(Decimal("1E-43"))
        '.0000000000000000000000000000000000000000001'
        >>> mumps_canonical_str(0)
        '0'
    """
    # --- int: trivial ---
    if isinstance(value, int):
        return str(value)

    # --- float → Decimal for precise decomposition ---
    if isinstance(value, float):
        if value == 0.0:
            return "0"
        d = Decimal(str(value))
    elif isinstance(value, Decimal):
        d = value
        if d == 0:
            return "0"
    else:
        # Shouldn't happen when called correctly, but be defensive.
        return str(value)

    # Normalize to remove trailing zeros before decomposition.
    # Without this, Decimal("0.123000...000") has raw exponent -51,
    # which would trip the exponent guard even though the value is just 0.123.
    # Use sufficient precision to avoid truncation of significant digits.
    num_digits = len(d.as_tuple().digits)
    with localcontext() as ctx:
        ctx.prec = max(ctx.prec, num_digits + 10)
        d = d.normalize()

    sign, digits, exponent = d.as_tuple()

    if not isinstance(exponent, int):
        # Infinity / NaN → "0"
        return "0"

    # Exponent guard (YDB: exponent < -43 ⇒ "0")
    if exponent < -43:
        return "0"

    if exponent >= 0:
        # Integer or large number
        result = "".join(str(dig) for dig in digits) + "0" * exponent
        if sign:
            result = "-" + result
    else:
        # Decimal number
        digits_str = "".join(str(dig) for dig in digits)
        exp = -exponent  # positive

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
            if not result:
                result = "0"

        if sign:
            result = "-" + result

    # Strip leading zeros (keep "0" for values like 0.5)
    if result.startswith("0") and len(result) > 1 and result[1] != ".":
        result = result.lstrip("0") or "0"
    if result.startswith("-0") and len(result) > 2 and result[2] != ".":
        result = "-" + result[2:].lstrip("0")

    return result


# ---------------------------------------------------------------------------
# String coercion  (FR-014)
# ---------------------------------------------------------------------------


def m_str(value: Any) -> str:
    """Convert any value to its MUMPS string representation.

    - ``str`` → returned as-is
    - MArray-like (``hasattr(value, "value")``) → unwrap, recurse
    - numeric types → :func:`mumps_canonical_str`
    - ``None`` / other → ``""``

    Args:
        value: Any Python value.

    Returns:
        MUMPS-style string representation.

    Examples:
        >>> m_str(7e-15)
        '.000000000000007'
        >>> m_str("hello")
        'hello'
        >>> m_str(0)
        '0'
    """
    # Handle MArray objects by extracting their value
    if hasattr(value, "value"):
        return m_str(value.value)

    if isinstance(value, Decimal):
        return mumps_canonical_str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value == 0.0:
            return "0"
        return mumps_canonical_str(value)

    # Non-numeric: straight ``str()``
    return str(value)


# ---------------------------------------------------------------------------
# Numeric coercion  (FR-014)
# ---------------------------------------------------------------------------


def m_num(value: Any) -> Union[int, float, Decimal]:
    """Convert a value to its MUMPS numeric interpretation.

    Implements ANSI MUMPS §7.1.4.5 numeric coercion rules:

    1. Already numeric → return (normalised int if whole).
    2. Strings: parse left-to-right from position 0.
       - Leading signs compose: ``++`` → ``+``, ``+-`` → ``-``.
       - Extract longest numeric prefix (only **uppercase** ``E`` for
         scientific notation).
       - First non-numeric/non-sign character (including space!) stops.

    Args:
        value: Any Python value.

    Returns:
        ``int``, ``float``, or ``Decimal``.

    Examples:
        >>> m_num(3)
        3
        >>> m_num("3A")
        3
        >>> m_num("A3")
        0
        >>> m_num("  42")
        0
        >>> m_num("+-5")
        -5
    """
    # MArray unwrap
    if hasattr(value, "value"):
        return m_num(value.value)

    # Decimal
    if isinstance(value, Decimal):
        if value == int(value):
            return int(value)
        return value

    # float → normalise
    if isinstance(value, float):
        if value == int(value):
            return int(value)
        return value

    if isinstance(value, int):
        return value

    # -- string processing --
    s = str(value)
    if not s:
        return 0

    # Leading signs
    sign = 1
    while s and s[0] in "+-":
        if s[0] == "-":
            sign = -sign
        s = s[1:]

    if not s:
        return 0

    # Longest numeric prefix (uppercase-E only)
    match = re.match(r"(\d*\.?\d*)(E[+-]?\d+)?", s)
    assert match is not None
    num_str = match.group(1)
    exp_str = match.group(2) or ""

    if not num_str or num_str == ".":
        return 0

    full_num_str = num_str + exp_str

    if "." in num_str or exp_str:
        result = Decimal(full_num_str) * sign
        if result == int(result):
            return int(result)
        return result
    else:
        return int(num_str) * sign


# ---------------------------------------------------------------------------
# Truth evaluation  (FR-014)
# ---------------------------------------------------------------------------


def m_truth(value: Any) -> bool:
    """Evaluate MUMPS truth value (ANSI §1.2.4).

    True if and only if ``m_num(value) != 0``.
    """
    return m_num(value) != 0


# ---------------------------------------------------------------------------
# Comparison  (FR-014)
# ---------------------------------------------------------------------------


def m_compare(left: Any, op: str, right: Any) -> int:
    """Perform MUMPS comparison with appropriate coercion.

    - ``"="``: canonical **string** equality (numerics normalised via
      :func:`m_str`, strings compared as-is).
    - ``"<"`` / ``">"``: **numeric** comparison (both coerced via
      :func:`m_num`).

    Returns ``1`` (true) or ``0`` (false).
    """
    # MArray unwrap
    while hasattr(left, "value"):
        left = left.value
    while hasattr(right, "value"):
        right = right.value

    if op == "=":
        left = m_str(left) if isinstance(left, (int, float, Decimal)) else str(left)
        right = m_str(right) if isinstance(right, (int, float, Decimal)) else str(right)
        return int(left == right)
    elif op == "<":
        return int(m_num(left) < m_num(right))
    elif op == ">":
        return int(m_num(left) > m_num(right))
    else:
        raise ValueError(f"Unknown MUMPS comparison operator: {op}")


# ---------------------------------------------------------------------------
# Decimal binary-operation helper  (FR-020 / S-06)
# ---------------------------------------------------------------------------


def _decimal_binop(left: Any, right: Any, op: str) -> Union[int, Decimal]:
    """Shared helper for 18-digit precision binary arithmetic.

    Args:
        left:  First operand (coerced via :func:`m_num`).
        right: Second operand (coerced via :func:`m_num`).
        op:    One of ``"+"``, ``"-"``, ``"*"``.

    Returns:
        ``int`` when the result is a whole number, ``Decimal`` otherwise.
    """
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
        if op == "+":
            result = left_dec + right_dec
        elif op == "-":
            result = left_dec - right_dec
        elif op == "*":
            result = left_dec * right_dec
        else:
            raise ValueError(f"Unsupported op: {op}")

        if result == int(result):
            return int(result)
        return result


def m_add(left: Any, right: Any) -> Union[int, Decimal]:
    """MUMPS addition with 18-digit precision."""
    return _decimal_binop(left, right, "+")


def m_sub(left: Any, right: Any) -> Union[int, Decimal]:
    """MUMPS subtraction with 18-digit precision."""
    return _decimal_binop(left, right, "-")


def m_mul(left: Any, right: Any) -> Union[int, Decimal]:
    """MUMPS multiplication with 18-digit precision."""
    return _decimal_binop(left, right, "*")


__all__ = [
    "mumps_canonical_str",
    "m_str",
    "m_num",
    "m_truth",
    "m_compare",
    "m_add",
    "m_sub",
    "m_mul",
]
