"""Tests for VIEW command parsing (§8.2.24).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.24

Migrated from: tests/unit/test_io_commands.py::TestViewCommand
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MRoutine


@pytest.mark.parser
class TestViewCommandParsing:
    """Parser-level tests for VIEW command (§8.2.24)."""

    def test_view_basic(self, command_metamodel):
        """VIEW keyword parses correctly (§8.2.24)."""
        model = command_metamodel.model_from_str("V X", "ViewCommand")
        assert model is not None

    def test_view_with_string(self, command_metamodel):
        """VIEW with string argument parses correctly (§8.2.24).

        Migrated from: test_io_commands.py::TestViewCommand::test_view_command_simple
        """
        model = command_metamodel.model_from_str('V "UNDEF"', "ViewCommand")
        assert model is not None

    def test_view_abbreviated(self):
        """V abbreviation parses correctly (§8.2.24)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n V X\n")

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MViewStatement"

    @pytest.mark.xfail(reason="Used in VistA: VIEW keywords like V 2:5:$C(X)")
    def test_view_implementation_keywords(self):
        """VIEW implementation-specific keywords used in VistA (§8.2.24)."""
        pytest.fail("Stub - implement test")
