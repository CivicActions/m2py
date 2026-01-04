"""Tests for IF command parsing (§8.2.9).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.9
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
class TestIfCommandParsing:
    """Parser-level tests for IF command (§8.2.9)."""

    def test_if_with_condition(self, command_metamodel):
        """I X=1 parses IF with single condition (§8.2.9)."""
        model = command_metamodel.model_from_str("I X=1", "IfCommand")
        assert model.conditions is not None
        assert len(model.conditions) == 1

    def test_if_argumentless(self, command_metamodel):
        """I (uses $TEST) parses IF without argument (§8.2.9)."""
        model = command_metamodel.model_from_str("I", "IfCommand")
        assert len(model.conditions) == 0

    def test_if_multiple_conditions(self, command_metamodel):
        """IF cond1,cond2 comma-separated conditions parses correctly (§8.2.9)."""
        model = command_metamodel.model_from_str("I X=1,Y=2", "IfCommand")
        assert model is not None
        assert len(model.conditions) == 2

    def test_if_abbreviated(self, command_metamodel):
        """IF X=1 full keyword parses same as I X=1 (§8.2.9)."""
        model = command_metamodel.model_from_str("IF X=1", "IfCommand")
        assert model.conditions is not None
        assert len(model.conditions) == 1

    def test_if_followed_by_commands(self):
        """IF condition followed by commands parses correctly (§8.2.9)."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine
        from m2py.asg.statements import MIfStatement, MSetStatement, MWriteStatement

        parser = MUMPSParser()
        routine = parser.parse("LBL\tI X=1 S Y=2 W Y\n")

        assert isinstance(routine, MRoutine)
        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MIfStatement)
        assert len(stmt.then_scope.statements) == 2
        assert isinstance(stmt.then_scope.statements[0], MSetStatement)
        assert isinstance(stmt.then_scope.statements[1], MWriteStatement)


@pytest.mark.parser
class TestElseCommandParsing:
    """Parser-level tests for ELSE command (§8.2.4)."""

    def test_else_simple(self, command_metamodel):
        """E parses ELSE command (§8.2.4)."""
        model = command_metamodel.model_from_str("E", "ElseCommand")
        assert model is not None

    def test_else_full_keyword(self, command_metamodel):
        """ELSE parses correctly (§8.2.4)."""
        model = command_metamodel.model_from_str("ELSE", "ElseCommand")
        assert model is not None
