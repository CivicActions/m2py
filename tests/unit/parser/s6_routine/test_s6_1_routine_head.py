"""Tests for Routine Head parsing (§6.1).

Tests verify the textX grammar correctly captures routine head syntax.

Reference: MUMPS 1995 ANSI Standard, Section 6.1
"""

import pytest

from m2py.asg import MRoutine


@pytest.mark.parser
class TestRoutineHeadParsing:
    """Parser-level tests for Routine Head (§6.1).

    The routine head is the first line of a routine, containing the routine name.
    """

    def test_routine_head_basic(self, parse_mumps):
        """Routine name on first line parses correctly (§6.1)."""
        result = parse_mumps("MYROUTINE\n S X=1\n Q")
        assert result is not None
        assert isinstance(result, MRoutine)
        assert len(result.labels) >= 1
        assert result.labels[0].name == "MYROUTINE"

    def test_routine_head_with_label(self, parse_mumps):
        """Routine with multiple labels parses correctly (§6.1)."""
        result = parse_mumps("MAIN\n S X=1\nSUB\n S Y=2\n Q")
        assert result is not None
        assert len(result.labels) == 2
        assert result.labels[0].name == "MAIN"
        assert result.labels[1].name == "SUB"

    def test_routine_head_name_validation(self, parse_mumps):
        """Routine head name follows identifier rules (§6.1).

        Label names can be:
        - Alphabetic: start with letter or %, followed by alphanumerics
        - Numeric: purely numeric (e.g., 123)
        """
        # Alphabetic label
        result = parse_mumps("TEST123\n Q")
        assert result.labels[0].name == "TEST123"

        # Label starting with %
        result = parse_mumps("%UTIL\n Q")
        assert result.labels[0].name == "%UTIL"

        # Numeric label
        result = parse_mumps("123\n Q")
        assert result.labels[0].name == "123"
