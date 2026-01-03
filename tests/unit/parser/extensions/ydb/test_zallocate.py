"""Tests for ZALLOCATE/ZDEALLOCATE command parsing (YDB extension).

Reference: YottaDB Z-Commands
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for ZALLOCATE/ZDEALLOCATE command tests."""
    grammar_dir = (
        Path(__file__).parent.parent.parent.parent.parent.parent
        / "src"
        / "m2py"
        / "grammar"
    )
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


@pytest.mark.parser
@pytest.mark.ydb
class TestZallocateParsing:
    """Parser-level tests for ZALLOCATE command (YDB)."""

    def test_zallocate_simple(self, command_metamodel):
        """za X - simple zallocate."""
        model = command_metamodel.model_from_str("za X", "ZAllocateCommand")
        assert model is not None
        assert len(model.targets) == 1

    def test_zallocate_with_timeout(self, command_metamodel):
        """za X:5 - with timeout."""
        model = command_metamodel.model_from_str("za X:5", "ZAllocateCommand")
        assert len(model.targets) == 1
        assert model.targets[0].timeout is not None

    def test_zallocate_list(self, command_metamodel):
        """Zallocate (@lvar,@gvar):60 - parenthesized list."""
        model = command_metamodel.model_from_str(
            "Zallocate (@lvar,@gvar):60", "ZAllocateCommand"
        )
        assert model.locklist is not None
        assert len(model.locklist.targets) == 2
        assert model.locklist.timeout is not None

    def test_zallocate_postcondition(self, command_metamodel):
        """Zallocate:'(i#2) X - with postcondition."""
        model = command_metamodel.model_from_str(
            "Zallocate:'(i#2) X", "ZAllocateCommand"
        )
        assert model.postcond is not None
        assert len(model.targets) == 1

    def test_zallocate_full(self, command_metamodel):
        """Zallocate:'(i#2) (@lvar,@gvar):60 - full syntax."""
        model = command_metamodel.model_from_str(
            "Zallocate:'(i#2) (@lvar,@gvar):60", "ZAllocateCommand"
        )
        assert model.postcond is not None
        assert model.locklist is not None
        assert len(model.locklist.targets) == 2


@pytest.mark.parser
@pytest.mark.ydb
class TestZdeallocateParsing:
    """Parser-level tests for ZDEALLOCATE command (YDB)."""

    def test_zdeallocate_simple(self, command_metamodel):
        """zd X - simple zdeallocate."""
        model = command_metamodel.model_from_str("zd X", "ZDeallocateCommand")
        assert model is not None
        assert len(model.targets) == 1

    def test_zdeallocate_full_spelling(self, command_metamodel):
        """zdeallocate X - full spelling."""
        model = command_metamodel.model_from_str("zdeallocate X", "ZDeallocateCommand")
        assert len(model.targets) == 1

    def test_zdeallocate_list(self, command_metamodel):
        """Zdeallocate (@lvar,@gvar) - parenthesized list."""
        model = command_metamodel.model_from_str(
            "Zdeallocate (@lvar,@gvar)", "ZDeallocateCommand"
        )
        assert model.locklist is not None
        assert len(model.locklist.targets) == 2

    def test_zdeallocate_postcondition(self, command_metamodel):
        """Zdeallocate:'(i#2) X - with postcondition."""
        model = command_metamodel.model_from_str(
            "Zdeallocate:'(i#2) X", "ZDeallocateCommand"
        )
        assert model.postcond is not None
        assert len(model.targets) == 1

    def test_zdeallocate_full(self, command_metamodel):
        """Zdeallocate:'(i#2) (@lvar,@gvar) - full syntax."""
        model = command_metamodel.model_from_str(
            "Zdeallocate:'(i#2) (@lvar,@gvar)", "ZDeallocateCommand"
        )
        assert model.postcond is not None
        assert model.locklist is not None

    def test_zdeallocate_multiple_targets(self, command_metamodel):
        """zd ^a,^b - multiple targets."""
        model = command_metamodel.model_from_str("zd ^a,^b", "ZDeallocateCommand")
        assert len(model.targets) == 2

    def test_zdeallocate_global(self, command_metamodel):
        """ZD ^GLOBAL - global variable."""
        model = command_metamodel.model_from_str("ZD ^GLOBAL", "ZDeallocateCommand")
        assert len(model.targets) == 1
