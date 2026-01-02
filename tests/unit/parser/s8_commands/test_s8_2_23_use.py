"""Tests for USE command parsing (§8.2.23).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.23

Migrated from:
- tests/unit/test_io_commands.py (test_use_command_simple)
- tests/unit/test_multi_arg_commands.py::TestMultiUse
- tests/unit/test_multi_arg_commands.py::TestCloseUseWithParams
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MUseStatement


@pytest.mark.parser
class TestUseCommandParsing:
    """Parser-level tests for USE command (§8.2.23)."""

    def test_use_basic(self):
        """USE device parses correctly (§8.2.23).

        Migrated from: test_io_commands.py::test_use_command_simple
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n U X\n")

        label = routine.labels[0]
        assert len(label.body.statements) == 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MUseStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr is not None

    def test_use_with_parameters(self):
        """USE device:(params) parses correctly (§8.2.23).

        Migrated from: test_multi_arg_commands.py::TestCloseUseWithParams::test_use_with_params
        """
        parser = MUMPSParser()
        routine = parser.parse('TEST\n U DEV:("PARAM")\n')

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MUseStatement)
        assert len(stmt.devices) == 1
        assert len(stmt.devices[0].parameters) == 1

    def test_use_multiple_devices(self):
        """USE dev1,dev2 parses correctly (§8.2.23).

        Migrated from: test_multi_arg_commands.py::TestMultiUse::test_multi_use
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n U DEV1,DEV2\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MUseStatement)
        assert len(stmt.devices) == 2

        assert stmt.devices[0].device_expr.name == "DEV1"
        assert stmt.devices[1].device_expr.name == "DEV2"

    def test_use_abbreviated(self):
        """U abbreviation parses correctly (§8.2.23)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n U X\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MUseStatement)
