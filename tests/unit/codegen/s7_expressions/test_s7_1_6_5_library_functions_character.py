"""Tests for CHARACTER Library Functions codegen (Annex I-1, §7.1.6.5).

Tests verify the generated Python code correctly implements CHARACTER library function behavior.
CHARACTER library functions handle character set operations.

Reference: MUMPS 1995 ANSI Standard, Annex I Section 1
Total: 5 CHARACTER library functions (note: LOWER, PATCODE, UPPER are in ^STRING per spec)
"""

import pytest


@pytest.mark.codegen
class TestCharacterLibraryFunctionsCodegen:
    """Codegen-level tests for CHARACTER library functions (Annex I-1).

    CHARACTER library provides character set collation and comparison functions.
    Note: Per the ANSI spec, LOWER, PATCODE, and UPPER are actually in ^STRING.
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $%COLLATE^CHARACTER codegen")
    def test_character_collate_codegen(self):
        """$%COLLATE^CHARACTER(A,B,CHARMOD) generates correct Python code (Annex I-1.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $%COMPARE^CHARACTER codegen")
    def test_character_compare_codegen(self):
        """$%COMPARE^CHARACTER(A,B,CHARMOD) generates correct Python code (Annex I-1.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $%LOWER^STRING codegen")
    def test_string_lower_codegen(self):
        """$%LOWER^STRING(A,CHARMOD) generates correct Python code (Annex I-1.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $%PATCODE^STRING codegen")
    def test_string_patcode_codegen(self):
        """$%PATCODE^STRING(A,PAT,CHARMOD) generates correct Python code (Annex I-1.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $%UPPER^STRING codegen")
    def test_string_upper_codegen(self):
        """$%UPPER^STRING(A,CHARMOD) generates correct Python code (Annex I-1.5)."""
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestAnsiLibraryErrorHandling:
    """Codegen tests for unimplemented ANSI library functions (LIM-014).

    ANSI standard library functions (^MATH, ^STRING, ^CHARACTER) have zero VistA
    usage. VistA uses Kernel Library Functions (^XLFMTH, etc.) instead.
    Unimplemented library functions should raise NotImplementedError (not
    AttributeError or ModuleNotFoundError).

    Reference: MUMPS 1995 ANSI Standard, Annex I
    Limitation: docs/limitations.md - LIM-014: ANSI Standard Library Functions
    """

    @pytest.mark.xfail(
        reason="LIM-014: ANSI library codegen not yet raising NotImplementedError"
    )
    def test_lim014_unimplemented_library_raises_not_implemented(self, generate_python):
        """Unimplemented ANSI library functions should raise NotImplementedError.

        The error should clearly indicate the function is not implemented, not
        produce an AttributeError or ModuleNotFoundError from import failures.
        """
        # Test CHARACTER library function
        with pytest.raises(NotImplementedError, match="COLLATE|CHARACTER|library"):
            generate_python('TEST S X=$$%COLLATE^CHARACTER("a","b") Q')

    @pytest.mark.xfail(
        reason="LIM-014: ANSI library codegen not yet raising NotImplementedError"
    )
    def test_lim014_unimplemented_math_raises_not_implemented(self, generate_python):
        """Unimplemented MATH library function should raise NotImplementedError.

        Extended MATH functions (matrix, complex, etc.) are not implemented.
        """
        with pytest.raises(NotImplementedError, match="MTXADD|MATH|library"):
            generate_python("TEST S X=$$%MTXADD^MATH(A,B) Q")
