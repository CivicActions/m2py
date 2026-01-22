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

    @pytest.mark.parametrize(
        "func_name,mumps_code,annex_ref",
        [
            pytest.param(
                "COLLATE^CHARACTER",
                'TEST S X=$$%COLLATE^CHARACTER("a","b","ASCII") Q',
                "Annex I-1.1",
                id="character_collate",
            ),
            pytest.param(
                "COMPARE^CHARACTER",
                'TEST S X=$$%COMPARE^CHARACTER("abc","def","ASCII") Q',
                "Annex I-1.2",
                id="character_compare",
            ),
            pytest.param(
                "LOWER^STRING",
                'TEST S X=$$%LOWER^STRING("HELLO","ASCII") Q',
                "Annex I-1.3",
                id="string_lower",
            ),
            pytest.param(
                "PATCODE^STRING",
                'TEST S X=$$%PATCODE^STRING("test","1N","ASCII") Q',
                "Annex I-1.4",
                id="string_patcode",
            ),
            pytest.param(
                "UPPER^STRING",
                'TEST S X=$$%UPPER^STRING("hello","ASCII") Q',
                "Annex I-1.5",
                id="string_upper",
            ),
        ],
    )
    def test_lim014_library_function_raises_error(
        self, func_name, mumps_code, annex_ref
    ):
        """$$%{func}(...) raises NotImplementedError with LIM-014 ({annex_ref})."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python(mumps_code)
