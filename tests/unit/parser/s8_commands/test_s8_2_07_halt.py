"""Tests for HALT command parsing (§8.2.7).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.7
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for HALT command tests."""
    grammar_dir = (
        Path(__file__).parent.parent.parent.parent.parent / "src" / "m2py" / "grammar"
    )
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


@pytest.mark.parser
class TestHaltCommandParsing:
    """Parser-level tests for HALT command (§8.2.7)."""

    def test_halt_basic(self, command_metamodel):
        """HALT parses correctly (§8.2.7)."""
        model = command_metamodel.model_from_str("HALT", "HaltCommand")
        assert model is not None

    def test_halt_abbreviated(self, parse_mumps):
        """H abbreviation (without argument) parses correctly (§8.2.7).

        H is the standard abbreviation for HALT. Note: H with an argument
        is HANG, not HALT.
        """
        from m2py.asg import MHaltStatement

        result = parse_mumps("TEST\n H\n Q")
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        assert isinstance(stmt, MHaltStatement)

    def test_halt_with_postcondition(self, parse_mumps):
        """HALT:condition parses correctly (§8.2.7).

        Postcondition controls whether HALT executes.
        """
        from m2py.asg import MHaltStatement

        result = parse_mumps("TEST\n H:X=1\n Q")
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        assert isinstance(stmt, MHaltStatement)
        assert stmt.postcondition is not None
