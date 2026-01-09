"""Name translation between MUMPS identifiers and Python identifiers.

MUMPS names can contain characters that are invalid in Python identifiers:
- % prefix (valid MUMPS, invalid Python)
- Pure numeric names like "01" (valid MUMPS label, invalid Python)
- Python keywords (if, for, etc.)

This module provides reversible translation between MUMPS and Python names.
"""

from __future__ import annotations

import keyword
import re


class NameTranslator:
    """Translates MUMPS names to valid Python identifiers and back.

    Translation rules (applied in order):
    1. % prefix: %FOO → _pct_FOO
    2. Pure numeric: 01 → _n_01
    3. Python keyword: if → _m_if
    4. Otherwise: identity (MUMPS names are usually valid Python)

    The prefixes are chosen to be unambiguous:
    - _pct_ can't conflict with MUMPS names (MUMPS doesn't allow underscore prefix)
    - _n_ can't conflict (same reason)
    - _m_ can't conflict (same reason)
    """

    # Pattern for pure numeric strings (valid MUMPS labels, invalid Python)
    _NUMERIC_PATTERN = re.compile(r"^[0-9]+$")

    def translate(self, mumps_name: str) -> str:
        """Convert MUMPS name to valid Python identifier.

        Args:
            mumps_name: MUMPS variable or label name

        Returns:
            Valid Python identifier

        Examples:
            >>> nt = NameTranslator()
            >>> nt.translate("TEST")
            'TEST'
            >>> nt.translate("%START")
            '_pct_START'
            >>> nt.translate("01")
            '_n_01'
            >>> nt.translate("if")
            '_m_if'
        """
        if not mumps_name:
            return mumps_name

        # Rule 1: % prefix
        if mumps_name.startswith("%"):
            return "_pct_" + mumps_name[1:]

        # Rule 2: Pure numeric
        if self._NUMERIC_PATTERN.match(mumps_name):
            return "_n_" + mumps_name

        # Rule 3: Python keyword
        if keyword.iskeyword(mumps_name):
            return "_m_" + mumps_name

        # Rule 4: Identity (most MUMPS names are valid Python)
        return mumps_name

    def reverse(self, python_name: str) -> str:
        """Recover original MUMPS name from Python identifier.

        Args:
            python_name: Python identifier (possibly translated)

        Returns:
            Original MUMPS name

        Examples:
            >>> nt = NameTranslator()
            >>> nt.reverse("TEST")
            'TEST'
            >>> nt.reverse("_pct_START")
            '%START'
            >>> nt.reverse("_n_01")
            '01'
            >>> nt.reverse("_m_if")
            'if'
        """
        if not python_name:
            return python_name

        # Reverse rule 1: _pct_ → %
        if python_name.startswith("_pct_"):
            return "%" + python_name[5:]

        # Reverse rule 2: _n_ → numeric
        if python_name.startswith("_n_"):
            return python_name[3:]

        # Reverse rule 3: _m_ → keyword
        if python_name.startswith("_m_"):
            return python_name[3:]

        # Identity
        return python_name


# Module-level singleton for convenience
_translator = NameTranslator()


def translate_name(mumps_name: str) -> str:
    """Convenience function to translate a MUMPS name to Python.

    Args:
        mumps_name: MUMPS variable or label name

    Returns:
        Valid Python identifier
    """
    return _translator.translate(mumps_name)


def reverse_name(python_name: str) -> str:
    """Convenience function to recover MUMPS name from Python.

    Args:
        python_name: Python identifier (possibly translated)

    Returns:
        Original MUMPS name
    """
    return _translator.reverse(python_name)


__all__ = ["NameTranslator", "translate_name", "reverse_name"]
