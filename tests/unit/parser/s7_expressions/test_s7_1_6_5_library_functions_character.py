"""Tests for CHARACTER Library Functions parsing (Annex I-1, §7.1.6.5).

Tests verify the textX grammar correctly captures CHARACTER library function syntax.
CHARACTER library functions handle character set operations.

Reference: MUMPS 1995 ANSI Standard, Annex I Section 1
Total: 5 CHARACTER library functions (note: LOWER, PATCODE, UPPER are in ^STRING per spec)
"""

import pytest

from m2py.parser.textx_classes import ExtrinsicFunction, LocalVariable


@pytest.mark.parser
class TestCharacterLibraryFunctionsParsing:
    """Parser-level tests for CHARACTER library functions (Annex I-1).

    CHARACTER library provides character set collation and comparison functions.
    Note: Per the ANSI spec, LOWER, PATCODE, and UPPER are actually in ^STRING.
    All functions are extrinsic functions called as $$FUNC^ROUTINE(args).
    """

    def test_character_collate(self, parse_mumps):
        """$%COLLATE^CHARACTER(A,B,CHARMOD) parses correctly (Annex I-1.1).

        COLLATE^CHARACTER returns collation order of strings.
        Arguments: A (string), B (string), CHARMOD (character modifier).
        Returns: -1 if A<B, 0 if A=B, 1 if A>B per collation rules.
        """
        routine = parse_mumps('TEST S X=$$COLLATE^CHARACTER(A,B,"M")')
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assign = stmt.assignments[0]

        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "COLLATE"
        assert assign.value.target.routine == "CHARACTER"
        assert len(assign.value.arguments) == 3

    def test_character_compare(self, parse_mumps):
        """$%COMPARE^CHARACTER(A,B,CHARMOD) parses correctly (Annex I-1.2).

        COMPARE^CHARACTER compares strings using character set rules.
        Arguments: A (string), B (string), CHARMOD (character modifier).
        Returns: -1, 0, or 1 based on comparison.
        """
        routine = parse_mumps("TEST S X=$$COMPARE^CHARACTER(A,B,CHARMOD)")
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assign = stmt.assignments[0]

        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "COMPARE"
        assert assign.value.target.routine == "CHARACTER"
        assert len(assign.value.arguments) == 3
        assert isinstance(assign.value.arguments[2].expression, LocalVariable)

    def test_string_lower(self, parse_mumps):
        """$%LOWER^STRING(A,CHARMOD) parses correctly (Annex I-1.3).

        LOWER^STRING converts string to lowercase.
        Arguments: A (string), CHARMOD (optional character modifier).
        Returns: Lowercase version of A.
        """
        routine = parse_mumps("TEST S X=$$LOWER^STRING(A)")
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assign = stmt.assignments[0]

        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "LOWER"
        assert assign.value.target.routine == "STRING"
        assert len(assign.value.arguments) == 1

    def test_string_patcode(self, parse_mumps):
        """$%PATCODE^STRING(A,PAT,CHARMOD) parses correctly (Annex I-1.4).

        PATCODE^STRING checks pattern code membership.
        Arguments: A (string), PAT (pattern code), CHARMOD (char modifier).
        Returns: 1 if A matches pattern code, 0 otherwise.
        """
        routine = parse_mumps('TEST S X=$$PATCODE^STRING(CHAR,"A",CHARMOD)')
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assign = stmt.assignments[0]

        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "PATCODE"
        assert assign.value.target.routine == "STRING"
        assert len(assign.value.arguments) == 3

    def test_string_upper(self, parse_mumps):
        """$%UPPER^STRING(A,CHARMOD) parses correctly (Annex I-1.5).

        UPPER^STRING converts string to uppercase.
        Arguments: A (string), CHARMOD (optional character modifier).
        Returns: Uppercase version of A.
        """
        routine = parse_mumps("TEST S X=$$UPPER^STRING(A)")
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assign = stmt.assignments[0]

        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "UPPER"
        assert assign.value.target.routine == "STRING"
        assert len(assign.value.arguments) == 1
