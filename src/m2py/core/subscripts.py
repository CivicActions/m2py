"""Subscript value canonicalization per MUMPS rules.

Canonical module for canonicalizing subscript values. Numeric subscripts
have a single canonical form; string subscripts are preserved unless
they represent canonical numeric values.

YDB behavior is authoritative for edge cases.
"""

from __future__ import annotations

import math
import re
from decimal import Decimal
from typing import Any, Union


class SubscriptCanonicalizer:
    """Canonicalize subscript values per MUMPS specification.

    MUMPS subscript canonicalization rules:
    - Numeric literals are canonicalized (01 → 1, 1.0 → 1)
    - Purely numeric strings that ARE in canonical form are canonicalized
    - Non-canonical numeric strings are PRESERVED ("01" stays "01")
    - Non-numeric strings are preserved exactly ("1X" stays "1X")

    Key insight: A(1) and A("1") access the SAME node, but A(1) and A("01")
    access DIFFERENT nodes because "01" is not in canonical form.
    """

    # Pattern to detect if a string is purely numeric (can be parsed as number)
    _NUMERIC_STRING_PATTERN = re.compile(r"^-?\.?\d+\.?\d*$")

    @staticmethod
    def canonicalize(value: Any) -> str:
        """Return canonical string representation of subscript value.

        Args:
            value: Subscript value (int, float, str, or object with .value)

        Returns:
            Canonical string representation

        Examples:
            >>> SubscriptCanonicalizer.canonicalize(1)
            '1'
            >>> SubscriptCanonicalizer.canonicalize(01)  # numeric literal
            '1'
            >>> SubscriptCanonicalizer.canonicalize(1.0)
            '1'
            >>> SubscriptCanonicalizer.canonicalize(1.5)
            '1.5'
            >>> SubscriptCanonicalizer.canonicalize("1")
            '1'
            >>> SubscriptCanonicalizer.canonicalize("01")  # Leading zero preserved!
            '01'
            >>> SubscriptCanonicalizer.canonicalize("1X")
            '1X'
        """
        # Handle MArray or other objects with .value attribute
        if hasattr(value, "value"):
            value = value.value

        # Numeric types: always canonicalize (including Decimal)
        if isinstance(value, (int, float, Decimal)):
            return SubscriptCanonicalizer.canonicalize_numeric(value)

        # String types: only canonicalize if already in canonical form
        if isinstance(value, str):
            # Check if it's a canonical numeric string
            if SubscriptCanonicalizer.is_canonical_numeric_string(value):
                # It's already canonical, return as-is
                return value
            # Non-canonical or non-numeric strings are preserved
            return value

        # Fall back to string conversion for other types
        return str(value)

    @staticmethod
    def canonicalize_numeric(n: Union[int, float, Decimal]) -> str:
        """Canonicalize a numeric value.

        Rules per MUMPS specification:
        - Integer: str(n)
        - Float equal to int: str(int(n))
        - Float with fractional: Remove trailing zeros, no leading zero before decimal

        Args:
            n: Numeric value (int, float, or Decimal)

        Returns:
            Canonical string representation

        Examples:
            >>> SubscriptCanonicalizer.canonicalize_numeric(1)
            '1'
            >>> SubscriptCanonicalizer.canonicalize_numeric(1.0)
            '1'
            >>> SubscriptCanonicalizer.canonicalize_numeric(1.50)
            '1.5'
            >>> SubscriptCanonicalizer.canonicalize_numeric(0.5)
            '.5'
            >>> SubscriptCanonicalizer.canonicalize_numeric(-1.5)
            '-1.5'
            >>> SubscriptCanonicalizer.canonicalize_numeric(-.5)
            '-.5'
        """
        # Handle Decimal type
        if isinstance(n, Decimal):
            # Check if it's effectively an integer
            if n == int(n):
                return str(int(n))
            # Format Decimal without scientific notation, preserving precision
            sign, digits, exponent = n.as_tuple()
            if not isinstance(exponent, int):
                return str(n)  # NaN/Infinity
            if exponent >= 0:
                return str(int(n))
            # Decimal number: reconstruct without scientific notation
            int_part = digits[:exponent] if exponent else ()
            frac_part = digits[exponent:]
            int_str = "".join(str(d) for d in int_part) if int_part else ""
            frac_str = "".join(str(d) for d in frac_part)
            if not int_str:
                int_str = ""
                frac_str = "0" * (-exponent - len(digits)) + frac_str
            result = int_str + "." + frac_str
            result = result.rstrip("0").rstrip(".")
            if result.startswith("0."):
                result = result[1:]
            if sign:
                result = "-" + result
            return result

        # Handle integer or float that equals integer
        if isinstance(n, int) or (
            isinstance(n, float) and n == int(n) and math.isfinite(n)
        ):
            return str(int(n))

        # Float with fractional part
        if isinstance(n, float):
            if not math.isfinite(n):
                # inf/nan - just convert to string
                return str(n)

            # Format and remove trailing zeros
            s = f"{n:.15g}"  # Use general format with high precision

            # Handle the case where we need to ensure decimal format
            if "." in s:
                # Remove trailing zeros after decimal point
                s = s.rstrip("0").rstrip(".")
                # If we stripped everything after decimal, result is integer
                if "." not in s:
                    return s

            # Remove leading zero before decimal for values like 0.5
            if s.startswith("0."):
                s = s[1:]  # "0.5" → ".5"
            elif s.startswith("-0."):
                s = "-" + s[2:]  # "-0.5" → "-.5"

            return s

    @staticmethod
    def is_canonical_numeric_string(s: str) -> bool:
        """Check if string represents a canonical numeric value.

        A string is canonical numeric if:
        - It can be parsed as a number
        - AND it equals its canonical form

        Args:
            s: String to check

        Returns:
            True if string is in canonical numeric form

        Examples:
            >>> SubscriptCanonicalizer.is_canonical_numeric_string("1")
            True
            >>> SubscriptCanonicalizer.is_canonical_numeric_string("01")
            False
            >>> SubscriptCanonicalizer.is_canonical_numeric_string("1.0")
            False
            >>> SubscriptCanonicalizer.is_canonical_numeric_string("1.5")
            True
            >>> SubscriptCanonicalizer.is_canonical_numeric_string(".5")
            True
            >>> SubscriptCanonicalizer.is_canonical_numeric_string("1X")
            False
            >>> SubscriptCanonicalizer.is_canonical_numeric_string("")
            False
        """
        if not s:
            return False

        # Try to parse as number using Decimal for precision
        # (float loses precision for very small numbers like -.0000000001)
        try:
            n = Decimal(s)
        except Exception:
            return False

        # Check if NaN or inf
        if not n.is_finite():
            return False

        # Get canonical form and compare
        canonical = SubscriptCanonicalizer.canonicalize_numeric(n)
        return s == canonical


__all__ = ["SubscriptCanonicalizer"]
