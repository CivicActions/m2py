"""Tests for KILL command parsing (§8.2.11).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.11
"""

import pytest


@pytest.mark.parser
class TestKillCommandParsing:
    """Parser-level tests for KILL command (§8.2.11)."""

    def test_simple_kill(self, command_metamodel):
        """K X - KILL single variable (§8.2.11)."""
        model = command_metamodel.model_from_str("K X", "KillCommand")
        assert len(model.args) == 1
        assert model.args[0].target is not None
        assert not model.args[0].exclusive  # False when not exclusive

    def test_kill_global(self, command_metamodel):
        """K ^GLOBAL - KILL global variable (§8.2.11)."""
        model = command_metamodel.model_from_str("K ^GLOBAL", "KillCommand")
        assert len(model.args) == 1
        assert model.args[0].target is not None

    def test_exclusive_kill(self, command_metamodel):
        """K (X,Y) - KILL exclusive form (§8.2.11)."""
        model = command_metamodel.model_from_str("K (X,Y)", "KillCommand")
        assert len(model.args) == 1
        assert model.args[0].exclusive  # True-ish when exclusive
        # textX uses 'except' attribute name from grammar
        assert len(getattr(model.args[0], "except")) == 2

    def test_multiple_exclusive_groups(self, command_metamodel):
        """K (X,Y,Z),(X,W) - multiple exclusive groups/intersection (§8.2.11)."""
        model = command_metamodel.model_from_str("K (X,Y,Z),(X,W)", "KillCommand")
        assert len(model.args) == 2
        assert model.args[0].exclusive
        assert model.args[1].exclusive
        assert getattr(model.args[0], "except") == ["X", "Y", "Z"]
        assert getattr(model.args[1], "except") == ["X", "W"]

    def test_mixed_exclusive_selective(self, command_metamodel):
        """K (X,W),Z - mixed exclusive and selective (§8.2.11)."""
        model = command_metamodel.model_from_str("K (X,W),Z", "KillCommand")
        assert len(model.args) == 2
        assert model.args[0].exclusive
        assert getattr(model.args[0], "except") == ["X", "W"]
        assert model.args[1].target is not None
