"""Tests for STRING Library Functions parsing (Annex I-3, §7.1.6.5).

Tests verify the textX grammar correctly captures STRING library function syntax.
STRING library functions are called as $$%FUNC^STRING or $$FUNC^STRING.

Reference: MUMPS 1995 ANSI Standard, Annex I Section 3
Total: 6 STRING library functions
"""

import pytest

from m2py.parser.textx_classes import ExtrinsicFunction, LocalVariable, StringLiteral


@pytest.mark.parser
class TestStringLibraryFunctionsParsing:
    """Parser-level tests for STRING library functions (Annex I-3).

    STRING library provides CRC, format, and string manipulation functions.
    All functions are extrinsic functions called as $$FUNC^STRING(args).
    """

    def test_string_crc16(self, parse_mumps):
        """$%CRC16^STRING(DATA,SEED) parses correctly (Annex I-3.1).

        CRC16^STRING computes 16-bit cyclic redundancy check.
        Arguments: DATA (string), SEED (optional initial value).
        """
        routine = parse_mumps('TEST S X=$$CRC16^STRING("DATA",SEED)')
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assign = stmt.assignments[0]

        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "CRC16"
        assert assign.value.target.routine == "STRING"
        assert len(assign.value.arguments) == 2
        assert isinstance(assign.value.arguments[0].expression, StringLiteral)
        assert isinstance(assign.value.arguments[1].expression, LocalVariable)

    def test_string_crc32(self, parse_mumps):
        """$%CRC32^STRING(DATA,SEED) parses correctly (Annex I-3.2).

        CRC32^STRING computes 32-bit cyclic redundancy check.
        Arguments: DATA (string), SEED (optional initial value).
        """
        routine = parse_mumps('TEST S X=$$CRC32^STRING("DATA",0)')
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assign = stmt.assignments[0]

        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "CRC32"
        assert assign.value.target.routine == "STRING"
        assert len(assign.value.arguments) == 2

    def test_string_crcccitt(self, parse_mumps):
        """$%CRCCCITT^STRING(DATA,SEED) parses correctly (Annex I-3.3).

        CRCCCITT^STRING computes CCITT polynomial CRC.
        Arguments: DATA (string), SEED (optional initial value).
        """
        routine = parse_mumps("TEST S X=$$CRCCCITT^STRING(DATA)")
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assign = stmt.assignments[0]

        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "CRCCCITT"
        assert assign.value.target.routine == "STRING"
        assert len(assign.value.arguments) == 1

    def test_string_format(self, parse_mumps):
        """$%FORMAT^STRING(DATA,WIDTH,FILL) parses correctly (Annex I-3.4).

        FORMAT^STRING formats data to specified width with optional fill char.
        Arguments: DATA (value), WIDTH (integer), FILL (optional char).
        """
        routine = parse_mumps('TEST S X=$$FORMAT^STRING(DATA,10," ")')
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assign = stmt.assignments[0]

        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "FORMAT"
        assert assign.value.target.routine == "STRING"
        assert len(assign.value.arguments) == 3

    def test_string_produce(self, parse_mumps):
        """$%PRODUCE^STRING(VALUE) parses correctly (Annex I-3.5).

        PRODUCE^STRING produces canonical string representation.
        Arguments: VALUE (expression).
        """
        routine = parse_mumps("TEST S X=$$PRODUCE^STRING(123.45)")
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assign = stmt.assignments[0]

        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "PRODUCE"
        assert assign.value.target.routine == "STRING"
        assert len(assign.value.arguments) == 1

    def test_string_replace(self, parse_mumps):
        """$%REPLACE^STRING(STRING,FIND,REPLACE) parses correctly (Annex I-3.6).

        REPLACE^STRING replaces occurrences of FIND with REPLACE.
        Arguments: STRING (source), FIND (search), REPLACE (replacement).
        """
        routine = parse_mumps('TEST S X=$$REPLACE^STRING(S,"OLD","NEW")')
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assign = stmt.assignments[0]

        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "REPLACE"
        assert assign.value.target.routine == "STRING"
        assert len(assign.value.arguments) == 3
