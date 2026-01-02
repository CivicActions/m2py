"""Tests for MERGE command parsing (§8.2.13).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.13
"""

import pytest


@pytest.mark.parser
class TestMergeCommandParsing:
    """Parser-level tests for MERGE command (§8.2.13)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: MERGE basic form")
    def test_merge_basic(self, parse_line):
        """MERGE dest=source parses correctly (§8.2.13)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: MERGE global to local")
    def test_merge_global_to_local(self, parse_line):
        """MERGE local=^GLOBAL parses correctly (§8.2.13)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: MERGE local to global")
    def test_merge_local_to_global(self, parse_line):
        """MERGE ^GLOBAL=local parses correctly (§8.2.13)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: MERGE with subscripts")
    def test_merge_with_subscripts(self, parse_line):
        """MERGE arr(1)=src(2) subscripted merge parses correctly (§8.2.13)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: MERGE multiple")
    def test_merge_multiple(self, parse_line):
        """MERGE a=b,c=d multiple merges parses correctly (§8.2.13)."""
        pytest.fail("Stub - implement test")
