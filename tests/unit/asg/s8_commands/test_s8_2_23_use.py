"""Tests for USE command ASG analysis (§8.2.23).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.23

Migrated from:
- tests/unit/test_io_commands.py (test_use_command_simple)
- tests/unit/test_multi_arg_commands.py::TestMultiUse
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MUseStatement


@pytest.mark.asg
class TestUseCommandAnalysis:
    """ASG-level tests for USE command analysis (§8.2.23)."""

    def test_use_command_node(self):
        """USE command creates correct ASG node (§8.2.23).

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


@pytest.mark.asg
class TestMultiUseAnalysis:
    """Tests for USE command with multiple devices (§8.2.23).

    Migrated from: tests/unit/test_multi_arg_commands.py::TestMultiUse
    """

    def test_single_use(self):
        """Single USE device works correctly (§8.2.23)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n U X\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MUseStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr.name == "X"

    def test_multi_use(self):
        """USE with multiple devices captures all devices (§8.2.23).

        Migrated from: test_multi_arg_commands.py::TestMultiUse::test_multi_use
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n U DEV1,DEV2\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MUseStatement)
        assert len(stmt.devices) == 2

        assert stmt.devices[0].device_expr.name == "DEV1"
        assert stmt.devices[1].device_expr.name == "DEV2"
