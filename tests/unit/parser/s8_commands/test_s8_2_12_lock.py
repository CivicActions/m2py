"""Tests for LOCK command parsing (§8.2.12).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.12
"""

import pytest


@pytest.mark.parser
class TestLockCommandParsing:
    """Parser-level tests for LOCK command (§8.2.12)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: LOCK basic form")
    def test_lock_basic(self, parse_line):
        """LOCK ^GLOBAL parses correctly (§8.2.12)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: LOCK increment")
    def test_lock_increment(self, parse_line):
        """LOCK +^GLOBAL incremental lock parses correctly (§8.2.12)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: LOCK decrement")
    def test_lock_decrement(self, parse_line):
        """LOCK -^GLOBAL decremental lock parses correctly (§8.2.12)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: LOCK with timeout")
    def test_lock_with_timeout(self, parse_line):
        """LOCK ^GLOBAL:timeout parses correctly (§8.2.12)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: LOCK multiple")
    def test_lock_multiple(self, parse_line):
        """LOCK (^A,^B) multiple locks parses correctly (§8.2.12)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: LOCK argumentless")
    def test_lock_argumentless(self, parse_line):
        """LOCK without argument (unlock all) parses correctly (§8.2.12)."""
        pytest.fail("Stub - implement test")
