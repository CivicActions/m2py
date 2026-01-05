"""Tests for CHARACTER Library Functions ASG analysis (Annex I-1, §7.1.6.5).

Tests verify the ASG correctly captures CHARACTER library function semantics.
CHARACTER library functions handle character set operations.

Reference: MUMPS 1995 ANSI Standard, Annex I Section 1
Total: 5 CHARACTER library functions (note: LOWER, PATCODE, UPPER are in ^STRING per spec)
"""

import pytest

from m2py.analysis.semantic_analyzer import analyze_expression
from m2py.asg.expressions import MActualParameter
from m2py.parser.textx_classes import ExtrinsicFunction
from tests.helpers.parsing import parse_expression


def verify_library_function(
    code: str, expected_label: str, expected_routine: str, expected_arg_count: int
):
    """Helper to verify a library function ASG structure.

    Args:
        code: MUMPS expression like '$$COLLATE^CHARACTER(A,B,"M")'
        expected_label: Expected function label like 'COLLATE'
        expected_routine: Expected routine name like 'CHARACTER' or 'STRING'
        expected_arg_count: Expected number of arguments
    """
    expr = parse_expression(code)
    asg = analyze_expression(expr)

    assert isinstance(asg, ExtrinsicFunction), (
        f"Expected ExtrinsicFunction, got {type(asg).__name__}"
    )
    assert asg.label == expected_label, (
        f"Expected label {expected_label}, got {asg.label}"
    )
    assert asg.routine == expected_routine, (
        f"Expected routine {expected_routine}, got {asg.routine}"
    )
    assert len(asg.arguments) == expected_arg_count, (
        f"Expected {expected_arg_count} args, got {len(asg.arguments)}"
    )

    # Verify all arguments are MActualParameter
    for i, arg in enumerate(asg.arguments):
        assert isinstance(arg, MActualParameter), (
            f"Arg {i} should be MActualParameter, got {type(arg).__name__}"
        )

    return asg


@pytest.mark.asg
class TestCharacterLibraryFunctionsASG:
    """ASG-level tests for CHARACTER library functions (Annex I-1).

    CHARACTER library provides character set collation and comparison functions.
    Note: Per the ANSI spec, LOWER, PATCODE, and UPPER are actually in ^STRING.
    """

    def test_character_collate_asg(self):
        """$%COLLATE^CHARACTER(A,B,CHARMOD) ASG captures function call semantics (Annex I-1.1)."""
        verify_library_function(
            '$$COLLATE^CHARACTER(A,B,"M")', "COLLATE", "CHARACTER", 3
        )

    def test_character_compare_asg(self):
        """$%COMPARE^CHARACTER(A,B,CHARMOD) ASG captures function call semantics (Annex I-1.2)."""
        verify_library_function(
            "$$COMPARE^CHARACTER(A,B,CHARMOD)", "COMPARE", "CHARACTER", 3
        )

    def test_string_lower_asg(self):
        """$%LOWER^STRING(A,CHARMOD) ASG captures function call semantics (Annex I-1.3)."""
        verify_library_function("$$LOWER^STRING(A)", "LOWER", "STRING", 1)

    def test_string_patcode_asg(self):
        """$%PATCODE^STRING(A,PAT,CHARMOD) ASG captures function call semantics (Annex I-1.4)."""
        verify_library_function(
            '$$PATCODE^STRING(CHAR,"A",CHARMOD)', "PATCODE", "STRING", 3
        )

    def test_string_upper_asg(self):
        """$%UPPER^STRING(A,CHARMOD) ASG captures function call semantics (Annex I-1.5)."""
        verify_library_function("$$UPPER^STRING(A)", "UPPER", "STRING", 1)
