"""MUMPS value model helper functions for code generation.

Canonical implementations now live in ``m2py.core.values``.  This module
re-exports them for backward compatibility with generated code and
existing imports throughout the codebase.

Feature: 019-foundation-cleanup  (FR-016)
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Union

# Re-export from canonical location  (FR-016)
from m2py.core.values import (
    m_add,
    m_compare,
    m_mul,
    m_num,
    m_str,
    m_sub,
    m_truth,
    mumps_canonical_str,
)


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
    "mumps_canonical_str",
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
