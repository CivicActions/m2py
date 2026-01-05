"""Tests for STRING Library Functions ASG analysis (Annex I-3, §7.1.6.5).

Tests verify the ASG correctly captures STRING library function semantics.
STRING library functions are called as $$%FUNC^STRING or $$FUNC^STRING.

Reference: MUMPS 1995 ANSI Standard, Annex I Section 3
Total: 6 STRING library functions
"""

import pytest

from m2py.analysis.semantic_analyzer import analyze_expression
from m2py.asg.expressions import MActualParameter
from m2py.parser.textx_classes import ExtrinsicFunction
from tests.helpers.parsing import parse_expression


def verify_string_function(code: str, expected_label: str, expected_arg_count: int):
    """Helper to verify a STRING library function ASG structure.

    Args:
        code: MUMPS expression like '$$CRC16^STRING("DATA",0)'
        expected_label: Expected function label like 'CRC16'
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
    assert asg.routine == "STRING", f"Expected routine STRING, got {asg.routine}"
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
class TestStringLibraryFunctionsASG:
    """ASG-level tests for STRING library functions (Annex I-3).

    STRING library provides CRC, format, and string manipulation functions.
    """

    def test_string_crc16_asg(self):
        """$%CRC16^STRING(DATA,SEED) ASG captures function call semantics (Annex I-3.1)."""
        verify_string_function('$$CRC16^STRING("DATA",0)', "CRC16", 2)

    def test_string_crc32_asg(self):
        """$%CRC32^STRING(DATA,SEED) ASG captures function call semantics (Annex I-3.2)."""
        verify_string_function('$$CRC32^STRING("DATA",0)', "CRC32", 2)

    def test_string_crcccitt_asg(self):
        """$%CRCCCITT^STRING(DATA,SEED) ASG captures function call semantics (Annex I-3.3)."""
        verify_string_function("$$CRCCCITT^STRING(DATA)", "CRCCCITT", 1)

    def test_string_format_asg(self):
        """$%FORMAT^STRING(DATA,WIDTH,FILL) ASG captures function call semantics (Annex I-3.4)."""
        verify_string_function('$$FORMAT^STRING(DATA,10," ")', "FORMAT", 3)

    def test_string_produce_asg(self):
        """$%PRODUCE^STRING(VALUE) ASG captures function call semantics (Annex I-3.5)."""
        verify_string_function("$$PRODUCE^STRING(123.45)", "PRODUCE", 1)

    def test_string_replace_asg(self):
        """$%REPLACE^STRING(STRING,FIND,REPLACE) ASG captures function call semantics (Annex I-3.6)."""
        verify_string_function('$$REPLACE^STRING(S,"OLD","NEW")', "REPLACE", 3)
