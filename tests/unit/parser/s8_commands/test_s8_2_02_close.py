"""Tests for CLOSE command parsing (§8.2.2).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.2

Migrated from:
- tests/unit/test_io_commands.py (test_close_command_simple)
- tests/unit/test_multi_arg_commands.py::TestMultiClose
- tests/unit/test_multi_arg_commands.py::TestCloseUseWithParams
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MCloseStatement


@pytest.mark.parser
class TestCloseCommandParsing:
    """Parser-level tests for CLOSE command (§8.2.2)."""

    def test_close_basic(self):
        """CLOSE device parses correctly (§8.2.2).

        Migrated from: test_io_commands.py::test_close_command_simple
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n C X\n")

        label = routine.labels[0]
        assert len(label.body.statements) == 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MCloseStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr is not None

    def test_close_with_parameters(self):
        """CLOSE device:(params) parses correctly (§8.2.2).

        Migrated from: test_multi_arg_commands.py::TestCloseUseWithParams::test_close_with_params
        """
        parser = MUMPSParser()
        routine = parser.parse('TEST\n C DEV:("PARAM")\n')

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MCloseStatement)
        assert len(stmt.devices) == 1
        assert len(stmt.devices[0].parameters) == 1

    def test_close_multiple_devices(self):
        """CLOSE dev1,dev2 parses correctly (§8.2.2).

        Migrated from: test_multi_arg_commands.py::TestMultiClose::test_multi_close
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n C DEV1,DEV2\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MCloseStatement)
        assert len(stmt.devices) == 2

        assert stmt.devices[0].device_expr.name == "DEV1"
        assert stmt.devices[1].device_expr.name == "DEV2"
