"""Tests for XECUTE command parsing (§8.2.26).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.26
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for XECUTE command tests."""
    grammar_dir = (
        Path(__file__).parent.parent.parent.parent.parent / "src" / "m2py" / "grammar"
    )
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


@pytest.mark.parser
class TestXecuteCommandParsing:
    """Parser-level tests for XECUTE command (§8.2.26)."""

    def test_xecute_string(self, command_metamodel):
        """X "S X=1" parses correctly (§8.2.26)."""
        model = command_metamodel.model_from_str('X "S X=1"', "XecuteCommand")
        assert len(model.args) == 1

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: XECUTE expression")
    def test_xecute_expression(self, parse_line):
        """XECUTE expr parses correctly (§8.2.26)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: XECUTE with postcondition")
    def test_xecute_with_postcondition(self, parse_line):
        """XECUTE expr:condition parses correctly (§8.2.26)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: XECUTE multiple")
    def test_xecute_multiple(self, parse_line):
        """XECUTE expr1,expr2 multiple expressions parses correctly (§8.2.26)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: XECUTE abbreviated")
    def test_xecute_abbreviated(self, parse_line):
        """X abbreviation parses correctly (§8.2.26)."""
        pytest.fail("Stub - implement test")
