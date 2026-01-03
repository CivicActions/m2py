"""Tests for BREAK command parsing (§8.2.1).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.1
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for BREAK command tests."""
    grammar_dir = (
        Path(__file__).parent.parent.parent.parent.parent / "src" / "m2py" / "grammar"
    )
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


@pytest.mark.parser
class TestBreakCommandParsing:
    """Parser-level tests for BREAK command (§8.2.1)."""

    def test_break_basic(self, command_metamodel):
        """B parses correctly (§8.2.1)."""
        model = command_metamodel.model_from_str("B", "BreakCommand")
        assert model is not None

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: BREAK argumentless")
    def test_break_argumentless(self, parse_line):
        """BREAK without arguments parses correctly (§8.2.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: BREAK abbreviated")
    def test_break_abbreviated(self, parse_line):
        """B abbreviation parses correctly (§8.2.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: BREAK with postcondition")
    def test_break_with_postcondition(self, parse_line):
        """BREAK:condition parses correctly (§8.2.1)."""
        pytest.fail("Stub - implement test")
