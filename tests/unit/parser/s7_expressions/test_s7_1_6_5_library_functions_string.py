"""Tests for STRING Library Functions parsing (Annex I-3, §7.1.6.5).

Tests verify the textX grammar correctly captures STRING library function syntax.
STRING library functions are called as $$%FUNC^STRING or $%FUNC^STRING.

Reference: MUMPS 1995 ANSI Standard, Annex I Section 3
Total: 6 STRING library functions
"""

import pytest


@pytest.mark.parser
class TestStringLibraryFunctionsParsing:
    """Parser-level tests for STRING library functions (Annex I-3).

    STRING library provides CRC, format, and string manipulation functions.
    """

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%CRC16^STRING library function parsing"
    )
    def test_string_crc16(self):
        """$%CRC16^STRING(DATA,SEED) parses correctly (Annex I-3.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%CRC32^STRING library function parsing"
    )
    def test_string_crc32(self):
        """$%CRC32^STRING(DATA,SEED) parses correctly (Annex I-3.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%CRCCCITT^STRING library function parsing"
    )
    def test_string_crcccitt(self):
        """$%CRCCCITT^STRING(DATA,SEED) parses correctly (Annex I-3.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%FORMAT^STRING library function parsing"
    )
    def test_string_format(self):
        """$%FORMAT^STRING(DATA,WIDTH,FILL) parses correctly (Annex I-3.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%PRODUCE^STRING library function parsing"
    )
    def test_string_produce(self):
        """$%PRODUCE^STRING(VALUE) parses correctly (Annex I-3.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%REPLACE^STRING library function parsing"
    )
    def test_string_replace(self):
        """$%REPLACE^STRING(STRING,FIND,REPLACE) parses correctly (Annex I-3.6)."""
        pytest.fail("Stub - implement test")
