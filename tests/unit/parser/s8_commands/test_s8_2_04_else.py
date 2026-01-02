"""Tests for ELSE command parsing (§8.2.4).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.4
"""

import pytest


@pytest.mark.parser
class TestElseCommandParsing:
    """Parser-level tests for ELSE command (§8.2.4)."""

    def test_simple_else(self, command_metamodel):
        """E - abbreviated ELSE command (§8.2.4)."""
        model = command_metamodel.model_from_str("E", "ElseCommand")
        assert model is not None

    def test_else_full_keyword(self, command_metamodel):
        """ELSE - full keyword form (§8.2.4)."""
        model = command_metamodel.model_from_str("ELSE", "ElseCommand")
        assert model is not None
