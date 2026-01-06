"""Tests for KILL command parsing (§8.2.11).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.11
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for KILL command tests."""
    grammar_dir = (
        Path(__file__).parent.parent.parent.parent.parent / "src" / "m2py" / "grammar"
    )
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


@pytest.mark.parser
class TestKillCommandParsing:
    """Parser-level tests for KILL command (§8.2.11)."""

    def test_kill_single_variable(self, command_metamodel):
        """K X parses correctly (§8.2.11)."""
        model = command_metamodel.model_from_str("K X", "KillCommand")
        assert len(model.args) == 1
        assert model.args[0].target is not None
        assert not model.args[0].exclusive  # False when not exclusive

    def test_kill_multiple_variables(self, command_metamodel):
        """KILL X,Y,Z multiple variables parses correctly (§8.2.11)."""
        model = command_metamodel.model_from_str("K X,Y,Z", "KillCommand")
        assert len(model.args) == 3
        assert model.args[0].target.name == "X"
        assert model.args[1].target.name == "Y"
        assert model.args[2].target.name == "Z"

    def test_kill_subscripted(self, command_metamodel):
        """KILL arr(1) subscripted variable parses correctly (§8.2.11)."""
        model = command_metamodel.model_from_str("K arr(1)", "KillCommand")
        assert len(model.args) == 1
        assert model.args[0].target.name == "arr"
        assert len(model.args[0].target.subscripts) == 1

    def test_kill_global(self, command_metamodel):
        """K ^GLOBAL parses correctly (§8.2.11)."""
        model = command_metamodel.model_from_str("K ^GLOBAL", "KillCommand")
        assert len(model.args) == 1
        assert model.args[0].target is not None

    def test_kill_exclusive(self, command_metamodel):
        """K (X,Y) exclusive form parses correctly (§8.2.11)."""
        model = command_metamodel.model_from_str("K (X,Y)", "KillCommand")
        assert len(model.args) == 1
        assert model.args[0].exclusive  # True-ish when exclusive
        # textX uses 'except' attribute name from grammar
        assert len(getattr(model.args[0], "except")) == 2

    def test_kill_multiple_exclusive_groups(self, command_metamodel):
        """K (X,Y,Z),(X,W) - multiple exclusive groups (intersection)."""
        model = command_metamodel.model_from_str("K (X,Y,Z),(X,W)", "KillCommand")
        assert len(model.args) == 2
        assert model.args[0].exclusive
        assert model.args[1].exclusive
        assert getattr(model.args[0], "except") == ["X", "Y", "Z"]
        assert getattr(model.args[1], "except") == ["X", "W"]

    def test_kill_mixed_exclusive_selective(self, command_metamodel):
        """K (X,W),Z - mixed exclusive and selective."""
        model = command_metamodel.model_from_str("K (X,W),Z", "KillCommand")
        assert len(model.args) == 2
        assert model.args[0].exclusive
        assert getattr(model.args[0], "except") == ["X", "W"]
        assert model.args[1].target is not None

    def test_kill_argumentless(self, command_metamodel):
        """KILL without argument parses correctly (§8.2.11)."""
        model = command_metamodel.model_from_str("K", "KillCommand")
        assert len(model.args) == 0

    def test_kill_with_postcondition(self, command_metamodel):
        """K:CLEANUP X parses command-level postcondition (§8.1.4).

        KILL can have postcondition, allowing conditional variable cleanup.
        """
        model = command_metamodel.model_from_str("K:CLEANUP X", "KillCommand")
        assert model.postcond is not None
        assert len(model.args) == 1
