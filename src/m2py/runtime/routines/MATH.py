"""MATH routine - Standard MUMPS mathematical library functions.

This module provides the %MATH routine as defined in the MUMPS standard.
Functions are callable via the extrinsic function syntax:
    $$%SQRT^MATH(x)
    $$%SIN^MATH(radians)
    etc.

Note: The MUMPS standard specifies math functions as library routines,
not intrinsic functions. This is the standard-compliant implementation.

Usage in MUMPS:
    W $$%SQRT^MATH(4)    ; Returns 2
    W $$%SIN^MATH(0)     ; Returns 0
    W $$%LOG^MATH(10)    ; Returns 2.302585...

All functions accept numeric values and return string representations
as per MUMPS conventions.

Function names use _pct_ prefix to match m2py's name translation rules:
    %SQRT → _pct_SQRT
    %SIN → _pct_SIN
    etc.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from m2py.runtime import MUMPSRuntime


def _pct_EXP(_rt: "MUMPSRuntime", x: str, _scope=None) -> str:
    """$$%EXP^MATH(x) - Returns e raised to the power of x.

    Args:
        _rt: Runtime instance (passed by extrinsic call mechanism)
        x: The exponent value
        _scope: Variable scope (unused, passed by extrinsic call mechanism)

    Returns:
        String representation of e^x
    """
    n = float(x)
    return str(math.exp(n))


def _pct_LOG(_rt: "MUMPSRuntime", x: str, _scope=None) -> str:
    """$$%LOG^MATH(x) - Returns the natural logarithm of x.

    Args:
        _rt: Runtime instance
        x: Must be positive
        _scope: Variable scope (unused)

    Returns:
        String representation of ln(x)

    Raises:
        ValueError: If x <= 0 (domain error)
    """
    n = float(x)
    if n <= 0:
        raise ValueError("DOMAIN error in %LOG: argument must be positive")
    return str(math.log(n))


# Alias: %LN is the same as %LOG
def _pct_LN(_rt: "MUMPSRuntime", x: str, _scope=None) -> str:
    """$$%LN^MATH(x) - Alias for %LOG (natural logarithm)."""
    return _pct_LOG(_rt, x, _scope)


def _pct_SQRT(_rt: "MUMPSRuntime", x: str, _scope=None) -> str:
    """$$%SQRT^MATH(x) - Returns the square root of x.

    Args:
        _rt: Runtime instance
        x: Must be non-negative
        _scope: Variable scope (unused)

    Returns:
        String representation of sqrt(x)

    Raises:
        ValueError: If x < 0 (domain error)
    """
    n = float(x)
    if n < 0:
        raise ValueError("DOMAIN error in %SQRT: argument must be non-negative")
    return str(math.sqrt(n))


def _pct_SIN(_rt: "MUMPSRuntime", x: str, _scope=None) -> str:
    """$$%SIN^MATH(x) - Returns the sine of x (in radians).

    Args:
        _rt: Runtime instance
        x: Angle in radians
        _scope: Variable scope (unused)

    Returns:
        String representation of sin(x), in range [-1, 1]
    """
    n = float(x)
    return str(math.sin(n))


def _pct_COS(_rt: "MUMPSRuntime", x: str, _scope=None) -> str:
    """$$%COS^MATH(x) - Returns the cosine of x (in radians).

    Args:
        _rt: Runtime instance
        x: Angle in radians
        _scope: Variable scope (unused)

    Returns:
        String representation of cos(x), in range [-1, 1]
    """
    n = float(x)
    return str(math.cos(n))


def _pct_TAN(_rt: "MUMPSRuntime", x: str, _scope=None) -> str:
    """$$%TAN^MATH(x) - Returns the tangent of x (in radians).

    Args:
        _rt: Runtime instance
        x: Angle in radians
        _scope: Variable scope (unused)

    Returns:
        String representation of tan(x)
    """
    n = float(x)
    return str(math.tan(n))


def _pct_ARCSIN(_rt: "MUMPSRuntime", x: str, _scope=None) -> str:
    """$$%ARCSIN^MATH(x) - Returns the arc sine of x (in radians).

    Args:
        _rt: Runtime instance
        x: Value in range [-1, 1]
        _scope: Variable scope (unused)

    Returns:
        String representation of arcsin(x), in range [-π/2, π/2]

    Raises:
        ValueError: If x not in [-1, 1] (domain error)
    """
    n = float(x)
    if n < -1 or n > 1:
        raise ValueError("DOMAIN error in %ARCSIN: argument must be in [-1, 1]")
    return str(math.asin(n))


# Alias: %ASIN is the same as %ARCSIN
def _pct_ASIN(_rt: "MUMPSRuntime", x: str, _scope=None) -> str:
    """$$%ASIN^MATH(x) - Alias for %ARCSIN."""
    return _pct_ARCSIN(_rt, x, _scope)


def _pct_ARCCOS(_rt: "MUMPSRuntime", x: str, _scope=None) -> str:
    """$$%ARCCOS^MATH(x) - Returns the arc cosine of x (in radians).

    Args:
        _rt: Runtime instance
        x: Value in range [-1, 1]
        _scope: Variable scope (unused)

    Returns:
        String representation of arccos(x), in range [0, π]

    Raises:
        ValueError: If x not in [-1, 1] (domain error)
    """
    n = float(x)
    if n < -1 or n > 1:
        raise ValueError("DOMAIN error in %ARCCOS: argument must be in [-1, 1]")
    return str(math.acos(n))


# Alias: %ACOS is the same as %ARCCOS
def _pct_ACOS(_rt: "MUMPSRuntime", x: str, _scope=None) -> str:
    """$$%ACOS^MATH(x) - Alias for %ARCCOS."""
    return _pct_ARCCOS(_rt, x, _scope)


def _pct_ARCTAN(_rt: "MUMPSRuntime", x: str, _scope=None) -> str:
    """$$%ARCTAN^MATH(x) - Returns the arc tangent of x (in radians).

    Args:
        _rt: Runtime instance
        x: Any real number
        _scope: Variable scope (unused)

    Returns:
        String representation of arctan(x), in range (-π/2, π/2)
    """
    n = float(x)
    return str(math.atan(n))


# Alias: %ATAN is the same as %ARCTAN
def _pct_ATAN(_rt: "MUMPSRuntime", x: str, _scope=None) -> str:
    """$$%ATAN^MATH(x) - Alias for %ARCTAN."""
    return _pct_ARCTAN(_rt, x, _scope)
