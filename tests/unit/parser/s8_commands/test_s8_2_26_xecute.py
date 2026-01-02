"""Tests for XECUTE command parsing (§8.2.26).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.26
"""

import pytest


@pytest.mark.parser
class TestXecuteCommandParsing:
    """Parser-level tests for XECUTE command (§8.2.26)."""

    def test_xecute_string(self, command_metamodel):
        """X "S X=1" - XECUTE string literal parses correctly (§8.2.26)."""
        model = command_metamodel.model_from_str('X "S X=1"', "XecuteCommand")
        assert len(model.args) == 1
