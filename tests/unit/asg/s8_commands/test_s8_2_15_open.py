"""Tests for OPEN command ASG analysis (§8.2.15).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.15

Migrated from:
- tests/unit/test_io_commands.py (OPEN tests)
- tests/unit/test_multi_arg_commands.py::TestMultiOpen
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MOpenStatement


@pytest.mark.asg
class TestOpenCommandAnalysis:
    """ASG-level tests for OPEN command analysis (§8.2.15)."""

    def test_open_command_node(self):
        """OPEN command creates correct ASG node (§8.2.15).

        Migrated from: test_io_commands.py::test_open_command_simple
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n O X\n")

        label = routine.labels[0]
        assert len(label.body.statements) == 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr is not None

    def test_open_device_expression(self):
        """OPEN device expression is analyzed (§8.2.15)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n O X\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr.name == "X"

    def test_open_parameters(self):
        """OPEN parameters are analyzed (§8.2.15).

        Migrated from: test_io_commands.py::test_open_command_with_params
        """
        parser = MUMPSParser()
        routine = parser.parse('TEST\n O X:("ABC")\n')

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 1
        assert len(stmt.devices[0].parameters) == 1

    def test_open_timeout(self):
        """OPEN timeout is analyzed (§8.2.15).

        Migrated from: test_io_commands.py::test_open_command_with_timeout
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n O X:5\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MOpenStatement)
        assert stmt.devices[0].timeout is not None
        assert stmt.devices[0].timeout.value == 5


@pytest.mark.asg
class TestMultiOpenAnalysis:
    """Tests for OPEN command with multiple devices (§8.2.15).

    Migrated from: tests/unit/test_multi_arg_commands.py::TestMultiOpen
    """

    def test_single_open(self):
        """Single OPEN device works correctly (§8.2.15)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n O X\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr.name == "X"

    def test_multi_open(self):
        """OPEN with multiple devices captures all devices (§8.2.15).

        Migrated from: test_multi_arg_commands.py::TestMultiOpen::test_multi_open
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n O DEV1,DEV2\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 2

        assert stmt.devices[0].device_expr.name == "DEV1"
        assert stmt.devices[1].device_expr.name == "DEV2"

    def test_open_with_params_multiple(self):
        """OPEN with parameters on multiple devices (§8.2.15).

        Migrated from: test_multi_arg_commands.py::TestMultiOpen::test_open_with_params_multiple
        """
        parser = MUMPSParser()
        routine = parser.parse('TEST\n O DEV1:("A"):5,DEV2:("B")\n')

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 2

        # First device has params and timeout
        assert stmt.devices[0].device_expr.name == "DEV1"
        assert len(stmt.devices[0].parameters) == 1
        assert stmt.devices[0].timeout is not None

        # Second device has params only
        assert stmt.devices[1].device_expr.name == "DEV2"
        assert len(stmt.devices[1].parameters) == 1
