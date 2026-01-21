"""Tests for CHARACTER Library Functions codegen (Annex I-1, §7.1.6.5).

Tests verify that CHARACTER library function calls raise NotImplementedError with LIM-014.
CHARACTER library functions handle character set operations.

Reference: MUMPS 1995 ANSI Standard, Annex I Section 1
Total: 5 CHARACTER library functions (note: LOWER, PATCODE, UPPER are in ^STRING per spec)

Per LIM-014: ANSI library routines (MATH, STRING, CHARACTER) have zero VistA usage.
VistA uses its own Kernel Library Functions instead.
"""

import pytest

from m2py.codegen import generate_python


@pytest.mark.codegen
class TestCharacterLibraryFunctionsCodegen:
    """Codegen-level tests for CHARACTER library functions (Annex I-1).

    CHARACTER library provides character set collation and comparison functions.
    Note: Per the ANSI spec, LOWER, PATCODE, and UPPER are actually in ^STRING.
    All should raise NotImplementedError with LIM-014.
    """

    def test_lim014_character_collate_raises_error(self):
        """$%COLLATE^CHARACTER(A,B,CHARMOD) raises NotImplementedError (Annex I-1.1)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%COLLATE^CHARACTER("a","b","ASCII") Q')

    def test_lim014_character_compare_raises_error(self):
        """$%COMPARE^CHARACTER(A,B,CHARMOD) raises NotImplementedError (Annex I-1.2)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%COMPARE^CHARACTER("abc","def","ASCII") Q')

    def test_lim014_string_lower_raises_error(self):
        """$%LOWER^STRING(A,CHARMOD) raises NotImplementedError (Annex I-1.3)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%LOWER^STRING("HELLO","ASCII") Q')

    def test_lim014_string_patcode_raises_error(self):
        """$%PATCODE^STRING(A,PAT,CHARMOD) raises NotImplementedError (Annex I-1.4)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%PATCODE^STRING("test","1N","ASCII") Q')

    def test_lim014_string_upper_raises_error(self):
        """$%UPPER^STRING(A,CHARMOD) raises NotImplementedError (Annex I-1.5)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%UPPER^STRING("hello","ASCII") Q')
