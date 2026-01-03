"""Tests for WRITE command parsing (§8.2.25).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.25
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
class TestWriteCommandParsing:
    """Parser-level tests for WRITE command (§8.2.25)."""

    def test_write_expression(self, command_metamodel):
        """W X writes expression value (§8.2.25)."""
        model = command_metamodel.model_from_str("W X", "WriteCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_write_string(self, command_metamodel):
        """W \"Hello\" writes string literal (§8.2.25)."""
        model = command_metamodel.model_from_str('W "Hello"', "WriteCommand")
        assert len(model.args) == 1

    def test_write_newline(self, command_metamodel):
        """W ! writes newline (§8.2.25)."""
        model = command_metamodel.model_from_str("W !", "WriteCommand")
        assert len(model.args) == 1

    def test_write_adjacent_newlines(self, command_metamodel):
        """W !! - two newlines without comma separator (§8.2.25)."""
        model = command_metamodel.model_from_str("W !!", "WriteCommand")
        assert len(model.args) == 2

    def test_write_triple_newlines(self, command_metamodel):
        """W !!! - three newlines (§8.2.25)."""
        model = command_metamodel.model_from_str("W !!!", "WriteCommand")
        assert len(model.args) == 3

    def test_write_mixed_format_controls(self, command_metamodel):
        """W !!,\"Test\",! - mix of adjacent and comma-separated (§8.2.25)."""
        model = command_metamodel.model_from_str('W !!,"Test",!', "WriteCommand")
        assert len(model.args) == 4

    def test_write_multiple(self, command_metamodel):
        """W \"Name: \",NAME,! writes multiple items (§8.2.25)."""
        model = command_metamodel.model_from_str('W "Name: ",NAME,!', "WriteCommand")
        assert len(model.args) == 3

    def test_write_tab(self, command_metamodel):
        """W ?10 writes tab to column 10 (§8.2.25)."""
        model = command_metamodel.model_from_str("W ?10", "WriteCommand")
        assert len(model.args) == 1

    def test_write_form_feed(self, command_metamodel):
        """W # writes form feed (§8.2.25)."""
        model = command_metamodel.model_from_str("W #", "WriteCommand")
        assert len(model.args) == 1

    def test_write_char_code(self, command_metamodel):
        """W *65 writes ASCII character 'A' (§8.2.25)."""
        model = command_metamodel.model_from_str("W *65", "WriteCommand")
        assert len(model.args) == 1

    def test_write_with_postcondition(self, command_metamodel):
        """W:DEBUG \"Debug mode\" writes conditionally (§8.1.4)."""
        model = command_metamodel.model_from_str('W:DEBUG "Debug mode"', "WriteCommand")
        assert model.postcond is not None

    def test_write_format_control(self, command_metamodel):
        """W !,?10,# format controls parse correctly (§8.2.25)."""
        # newline
        model = command_metamodel.model_from_str("W !", "WriteCommand")
        assert len(model.args) == 1
        # tab
        model = command_metamodel.model_from_str("W ?10", "WriteCommand")
        assert len(model.args) == 1
        # form feed
        model = command_metamodel.model_from_str("W #", "WriteCommand")
        assert len(model.args) == 1

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: WRITE argumentless")
    def test_write_argumentless(self, command_metamodel):
        """WRITE without argument parses correctly (§8.2.25).

        Note: WRITE without arguments is not a standard MUMPS pattern but
        should still parse. This is left as stub pending clarification.
        """
        pytest.fail("Stub - implement test or confirm argumentless WRITE behavior")

    def test_write_abbreviated(self, command_metamodel):
        """W abbreviation parses correctly (§8.2.25)."""
        model_abbrev = command_metamodel.model_from_str("W X", "WriteCommand")
        model_full = command_metamodel.model_from_str("WRITE X", "WriteCommand")
        # Both should parse correctly
        assert model_abbrev is not None
        assert model_full is not None
        assert len(model_abbrev.args) == len(model_full.args)


@pytest.mark.parser
class TestWriteStatementGrammar:
    """Test WRITE command parsing via MUMPSParser full routine parsing."""

    def test_simple_write(self):
        """WRITE with single string argument."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tW "Hello"\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_write_abbreviated(self):
        """W abbreviation should work same as WRITE."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tW !!\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_write_format_codes(self):
        """WRITE with format codes (!, #, ?n)."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tW !!,"Test",!\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_write_variable(self):
        """WRITE with variable reference."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tW X\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
