"""Subscript value canonicalization per MUMPS rules.

This module provides the **single source of truth** for canonicalizing
subscript values. Numeric subscripts have a single canonical form;
string subscripts are preserved unless they represent canonical numeric values.

Constitution II: YDB behavior is authoritative for edge cases.

Feature: 018-unified-variable-system
Requirements: FR-003, FR-004
"""

from __future__ import annotations

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

        Delegates to mumps_canonical_str from core.values (FR-013).

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
        from m2py.core.values import mumps_canonical_str

        return mumps_canonical_str(n)

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
