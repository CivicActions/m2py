"""Tests for KILL command parsing (§8.2.11).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.11
"""

import pytest


@pytest.mark.parser
class TestKillCommandParsing:
    """Parser-level tests for KILL command (§8.2.11)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KILL single variable")
    def test_kill_single_variable(self, parse_line):
        """KILL X parses correctly (§8.2.11)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KILL multiple variables")
    def test_kill_multiple_variables(self, parse_line):
        """KILL X,Y,Z multiple variables parses correctly (§8.2.11)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KILL subscripted variable")
    def test_kill_subscripted(self, parse_line):
        """KILL arr(1) subscripted variable parses correctly (§8.2.11)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KILL global variable")
    def test_kill_global(self, parse_line):
        """KILL ^GLOBAL parses correctly (§8.2.11)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KILL exclusive form")
    def test_kill_exclusive(self, parse_line):
        """KILL (X,Y) exclusive form parses correctly (§8.2.11)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KILL argumentless")
    def test_kill_argumentless(self, parse_line):
        """KILL without argument parses correctly (§8.2.11)."""
        pytest.fail("Stub - implement test")
