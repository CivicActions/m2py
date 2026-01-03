"""Tests for $KEY value parsing (§8.2.21).

Shares section numbering with TROLLBACK.
Reference: MUMPS 1995 ANSI Standard, Section 8.2.21
"""

import pytest


@pytest.mark.parser
class TestKValueParsing:
    """Parser-level tests for $KEY value (§8.2.21)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KVALUE basic form")
    def test_kvalue_basic(self, parse_line):
        """KVALUE parses correctly (§8.2.21)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KVALUE with arguments")
    def test_kvalue_with_arguments(self, parse_line):
        """KVALUE with arguments parses correctly (§8.2.21)."""
        pytest.fail("Stub - implement test")
