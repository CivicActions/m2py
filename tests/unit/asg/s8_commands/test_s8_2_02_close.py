"""Tests for CLOSE command ASG analysis (§8.2.2).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.2

Migrated from:
- tests/unit/test_io_commands.py (test_close_command_simple)
- tests/unit/test_multi_arg_commands.py::TestMultiClose
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MCloseStatement


@pytest.mark.asg
class TestCloseCommandAnalysis:
    """ASG-level tests for CLOSE command analysis (§8.2.2)."""

    def test_close_command_node(self):
        """CLOSE command creates correct ASG node (§8.2.2).

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

    def test_close_device_tracking(self):
        """CLOSE device expression is tracked (§8.2.2).

        Migrated from: test_multi_arg_commands.py::TestMultiClose::test_single_close
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n C X\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MCloseStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr.name == "X"


@pytest.mark.asg
class TestMultiCloseAnalysis:
    """Tests for CLOSE command with multiple devices (§8.2.2).

    Migrated from: tests/unit/test_multi_arg_commands.py::TestMultiClose
    """

    def test_single_close(self):
        """Single CLOSE device works correctly (§8.2.2)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n C X\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MCloseStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr.name == "X"

    def test_multi_close(self):
        """CLOSE with multiple devices captures all devices (§8.2.2).

        Migrated from: test_multi_arg_commands.py::TestMultiClose::test_multi_close
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n C DEV1,DEV2\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MCloseStatement)
        assert len(stmt.devices) == 2

        assert stmt.devices[0].device_expr.name == "DEV1"
        assert stmt.devices[1].device_expr.name == "DEV2"
