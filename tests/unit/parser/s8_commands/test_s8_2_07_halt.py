"""Tests for HALT command parsing (§8.2.7).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.7
"""

import pytest


@pytest.mark.parser
class TestHaltCommandParsing:
    """Parser-level tests for HALT command (§8.2.7)."""

    def test_halt_basic(self, command_metamodel):
        """HALT parses correctly (§8.2.7)."""
        model = command_metamodel.model_from_str("HALT", "HaltCommand")
        assert model is not None
