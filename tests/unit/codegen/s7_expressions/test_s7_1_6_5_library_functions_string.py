"""Tests for STRING Library Functions codegen (Annex I-3, §7.1.6.5).

Tests verify that STRING library function calls raise NotImplementedError with LIM-014.
STRING library functions are called as $$%FUNC^STRING or $%FUNC^STRING.

Reference: MUMPS 1995 ANSI Standard, Annex I Section 3
Total: 6 STRING library functions

Per LIM-014: ANSI library routines (MATH, STRING, CHARACTER) have zero VistA usage.
VistA uses its own Kernel Library Functions instead.
"""

import pytest

from m2py.codegen import generate_python


@pytest.mark.codegen
class TestStringLibraryFunctionsCodegen:
    """Codegen-level tests for STRING library functions (Annex I-3).

    STRING library provides CRC, format, and string manipulation functions.
    All should raise NotImplementedError with LIM-014.
    """

    def test_lim014_string_crc16_raises_error(self):
        """$%CRC16^STRING(DATA,SEED) raises NotImplementedError (Annex I-3.1)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%CRC16^STRING("data",0) Q')

    def test_lim014_string_crc32_raises_error(self):
        """$%CRC32^STRING(DATA,SEED) raises NotImplementedError (Annex I-3.2)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%CRC32^STRING("data",0) Q')

    def test_lim014_string_crcccitt_raises_error(self):
        """$%CRCCCITT^STRING(DATA,SEED) raises NotImplementedError (Annex I-3.3)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%CRCCCITT^STRING("data",0) Q')

    def test_lim014_string_format_raises_error(self):
        """$%FORMAT^STRING(DATA,WIDTH,FILL) raises NotImplementedError (Annex I-3.4)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%FORMAT^STRING("test",10," ") Q')

    def test_lim014_string_produce_raises_error(self):
        """$%PRODUCE^STRING(VALUE) raises NotImplementedError (Annex I-3.5)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%PRODUCE^STRING(123) Q")

    def test_lim014_string_replace_raises_error(self):
        """$%REPLACE^STRING(STRING,FIND,REPLACE) raises NotImplementedError (Annex I-3.6)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%REPLACE^STRING("hello","l","r") Q')
