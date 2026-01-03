"""Tests for VIEW command parsing (§8.2.24).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.24
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for VIEW command tests."""
    grammar_dir = (
        Path(__file__).parent.parent.parent.parent.parent / "src" / "m2py" / "grammar"
    )
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


@pytest.mark.parser
class TestViewCommandParsing:
    """Parser-level tests for VIEW command (§8.2.24)."""

    def test_view_basic(self, command_metamodel):
        """V 0 parses correctly (§8.2.24)."""
        model = command_metamodel.model_from_str("V 0", "ViewCommand")
        assert len(model.args) == 1

    def test_view_keyword_value(self, command_metamodel):
        """VIEW "JOBPID":1 - keyword with colon-separated value."""
        model = command_metamodel.model_from_str('VIEW "JOBPID":1', "ViewCommand")
        assert len(model.args) == 1
        # Check that the arg has the colon-separated value
        assert hasattr(model.args[0], "values")
        assert len(model.args[0].values) == 1

    def test_view_keyword_multiple_values(self, command_metamodel):
        """VIEW "trace":1:"^trace" - keyword with multiple colon-separated values."""
        model = command_metamodel.model_from_str(
            'VIEW "trace":1:"^trace"', "ViewCommand"
        )
        assert len(model.args) == 1
        assert len(model.args[0].values) == 2

    def test_view_mixed_case(self, command_metamodel):
        """View "GVDUPSETNOOP":0 - mixed case command."""
        model = command_metamodel.model_from_str('View "GVDUPSETNOOP":0', "ViewCommand")
        assert len(model.args) == 1
        assert len(model.args[0].values) == 1

    def test_view_multiple_args(self, command_metamodel):
        """VIEW "key1":val1,"key2":val2 - multiple comma-separated args."""
        model = command_metamodel.model_from_str(
            'VIEW "key1":val1,"key2":val2', "ViewCommand"
        )
        assert len(model.args) == 2

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: VIEW with arguments")
    def test_view_with_arguments(self, parse_line):
        """VIEW keyword:args parses correctly (§8.2.24)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: VIEW abbreviated")
    def test_view_abbreviated(self, parse_line):
        """V abbreviation parses correctly (§8.2.24)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.skip(
        reason="Implementation-defined: VIEW keywords are implementation-specific"
    )
    def test_view_implementation_keywords(self):
        """VIEW implementation-specific keywords are out of scope (§8.2.24)."""
        pass
