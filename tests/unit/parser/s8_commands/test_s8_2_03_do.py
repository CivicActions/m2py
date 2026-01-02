"""Tests for DO command parsing (§8.2.3).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.3
"""

import pytest


@pytest.mark.parser
class TestDoCommandParsing:
    """Parser-level tests for DO command (§8.2.3)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO with label")
    def test_do_with_label(self, parse_line):
        """DO LABEL parses correctly (§8.2.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO with external routine")
    def test_do_external_routine(self, parse_line):
        """DO LABEL^ROUTINE parses correctly (§8.2.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO with arguments")
    def test_do_with_arguments(self, parse_line):
        """DO LABEL(arg1,arg2) parses correctly (§8.2.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO with label and offset")
    def test_do_with_offset(self, parse_line):
        """DO LABEL+3 parses correctly (§8.2.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO argumentless (block)")
    def test_do_argumentless_block(self, parse_mumps):
        """DO without argument (block start) parses correctly (§8.2.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO with postcondition")
    def test_do_with_postcondition(self, parse_line):
        """DO:condition LABEL parses correctly (§8.2.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO with pass by reference")
    def test_do_pass_by_reference(self, parse_line):
        """DO LABEL(.var) pass by reference parses correctly (§8.2.3)."""
        pytest.fail("Stub - implement test")
