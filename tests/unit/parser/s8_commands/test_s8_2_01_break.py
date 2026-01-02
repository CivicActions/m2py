"""Tests for BREAK command parsing (§8.2.1).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.1
"""

import pytest


@pytest.mark.parser
class TestBreakCommandParsing:
    """Parser-level tests for BREAK command (§8.2.1)."""

    def test_break_basic(self, command_metamodel):
        """B - BREAK parses correctly (§8.2.1)."""
        model = command_metamodel.model_from_str("B", "BreakCommand")
        assert model is not None
