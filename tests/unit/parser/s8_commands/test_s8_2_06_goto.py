"""Tests for GOTO command parsing (§8.2.6).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.6
"""

import pytest
from pathlib import Path
from textx import metamodel_from_file
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))
from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar metamodel with custom classes."""
    grammar_dir = (
        Path(__file__).parent.parent.parent.parent.parent / "src" / "m2py" / "grammar"
    )
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


@pytest.mark.parser
class TestGotoCommandParsing:
    """Parser-level tests for GOTO command (§8.2.6)."""

    def test_goto_with_label(self, command_metamodel):
        """G LABEL parses GOTO to label (§8.2.6)."""
        model = command_metamodel.model_from_str("G LABEL", "GotoCommand")
        assert len(model.targets) == 1

    def test_goto_external_routine(self, command_metamodel):
        """G LABEL^ROUTINE parses GOTO to external routine (§8.2.6)."""
        model = command_metamodel.model_from_str("G LABEL^ROUTINE", "GotoCommand")
        target = model.targets[0]
        assert target.label.routine == "ROUTINE"

    def test_goto_with_offset(self, command_metamodel):
        """G LABEL+5 parses GOTO with offset (§8.2.6)."""
        model = command_metamodel.model_from_str("G LABEL+5", "GotoCommand")
        target = model.targets[0]
        assert target.label.offset is not None

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: GOTO with postcondition")
    def test_goto_with_postcondition(self, command_metamodel):
        """G:condition LABEL parses correctly (§8.2.6)."""
        pytest.fail("Stub - implement test")

    def test_goto_abbreviated(self, command_metamodel):
        """G LABEL parses abbreviated form (§8.2.6)."""
        model = command_metamodel.model_from_str("G LABEL", "GotoCommand")
        assert len(model.targets) == 1

    def test_goto_multiple_targets(self, command_metamodel):
        """G ABC:X=1,DEF:Y=2 parses GOTO with multiple targets with postconditions (§8.2.6)."""
        model = command_metamodel.model_from_str("G ABC:X=1,DEF:Y=2", "GotoCommand")
        assert len(model.targets) == 2
        assert model.targets[0].postcond is not None
        assert model.targets[1].postcond is not None

    def test_goto_routine_only(self, command_metamodel):
        """G ^ROUTINE parses GOTO to routine entry (§8.2.6)."""
        model = command_metamodel.model_from_str("G ^ROUTINE", "GotoCommand")
        target = model.targets[0]
        assert target.label.routine == "ROUTINE"

    def test_goto_conditional(self, command_metamodel):
        """G:X LABEL parses conditional GOTO (§8.2.6)."""
        model = command_metamodel.model_from_str("G:X LABEL", "GotoCommand")
        assert model.postcond is not None

    def test_goto_arg_postcondition(self, command_metamodel):
        """G ABC:X=1 - postcondition on target argument (§8.2.6)."""
        model = command_metamodel.model_from_str("G ABC:X=1", "GotoCommand")
        assert model.postcond is None  # Command postcond is None
        assert model.targets[0].postcond is not None  # Target postcond is set
        assert model.targets[0].label.label == "ABC"
