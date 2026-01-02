"""Tests for Routine Head parsing (§6.1).

Tests verify the textX grammar correctly captures routine head syntax.

Reference: MUMPS 1995 ANSI Standard, Section 6.1
"""

import pytest


@pytest.mark.parser
class TestRoutineHeadParsing:
    """Parser-level tests for Routine Head (§6.1).

    The routine head is the first line of a routine, containing the routine name.
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: routine head basic form")
    def test_routine_head_basic(self, parse_mumps):
        """Routine name on first line parses correctly (§6.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: routine head with label")
    def test_routine_head_with_label(self, parse_mumps):
        """Routine with label on first line parses correctly (§6.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: routine head validation")
    def test_routine_head_name_validation(self, parse_mumps):
        """Routine head name follows identifier rules (§6.1)."""
        pytest.fail("Stub - implement test")
